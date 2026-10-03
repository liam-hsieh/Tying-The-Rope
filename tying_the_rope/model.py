"""Main model class for Tying-The-Rope site-product qualification optimization."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import scipy.io as sio

from tying_the_rope.config import ModelConfig
from tying_the_rope.data_loader import InputDataSet, load_input_file
from tying_the_rope.exporter import export_results_to_excel
from tying_the_rope.lp_solver import LPSolver


class TyingTheRope:
    """End-to-end site-product qualification simulation and optimization engine."""

    def __init__(
        self,
        input_file: Union[str, Path] = "Inputs/examples.xlsx",
        sl_target: float = 0.0,
        max_round: int = 20,
        num_scenario: int = 100,
        config: Optional[ModelConfig] = None,
        output_dir: Optional[Union[str, Path]] = None,
    ):
        if config is None:
            self.config = ModelConfig(
                sl_target=sl_target,
                max_round=max_round,
                num_scenario=num_scenario,
            )
        else:
            self.config = config
            if sl_target > 0:
                self.config.sl_target = sl_target
            if max_round != 20:
                self.config.max_round = max_round
            if num_scenario != 100:
                self.config.num_scenario = num_scenario

        # Load datasets from input Excel
        self.data: InputDataSet = load_input_file(
            input_file,
            output_base_dir="outputs" if output_dir is None else output_dir,
        )
        self.basic_info = self.data.basic_info
        self.dims = self.data.dims
        self.demand = self.data.demand
        self.capacity = self.data.capacity
        self.min_util = self.data.min_util
        self.qmat = {k: v.copy() for k, v in self.data.qmat.items()}

        # Identify allowable primary (exclusion == 0) and secondary (exclusion == 2) options
        r_mat = self.qmat["exclusion"]
        self.primary_options = np.argwhere(r_mat == 0)      # pairs of (prod_idx, site_idx)
        self.secondary_options = np.argwhere(r_mat == 2)

        # Set reference quarter: default to quarter with highest forecast demand
        if self.config.ref_quarter is None:
            total_fcst_per_quarter = np.sum(self.demand.fcst, axis=0)
            self.ref_quarter = int(np.argmax(total_fcst_per_quarter))
        else:
            self.ref_quarter = int(self.config.ref_quarter)

        # Initialize progress table header
        site_names = self.basic_info.sites
        self.progress: List[List[Any]] = [
            [
                "name",
                "num_link",
                "product",
                "site",
                "option type",
                "Obj_mean",
                "SL_mean",
                *[f"{s}_Ld_mean" for s in site_names],
                *[f"{s}_Ld_P10" for s in site_names],
                *[f"{s}_LdP5" for s in site_names],
            ]
        ]

        # Nested dictionaries: quarter_idx -> matrix_name -> stats / records
        self.stat: Dict[int, Dict[str, Any]] = {q: {} for q in range(self.dims.num_quarter)}
        self.recordset: Dict[int, Dict[str, Any]] = {q: {} for q in range(self.dims.num_quarter)}

        # Random demand scenarios storage
        self.rand_demand: Dict[int, np.ndarray] = {}

        # Instantiate LP/MIP solver
        self.solver = LPSolver(
            num_prod=self.dims.num_prod,
            num_site=self.dims.num_site,
            margin=self.demand.margin,
            cost_matrix=self.data.cost_matrix,
            wt_min_u_obj=self.config.wt_min_u_obj,
            big_m=self.config.big_m,
            mode=self.config.mode,
        )

    def create_rand_demand(
        self,
        mat_file: Optional[Union[str, Path]] = None,
        seed: Optional[int] = None,
        save_mat: bool = True,
    ) -> Dict[int, np.ndarray]:
        """Generates or loads Monte Carlo demand scenarios for all quarters.
        
        Args:
            mat_file: Path to existing .mat file with 'RandDemand'.
            seed: Optional random seed for reproducible sampling.
            save_mat: If True, saves generated scenarios to output directory.
            
        Returns:
            Dictionary mapping quarter index to demand array of shape (num_prod, num_scenarios).
        """
        if mat_file is not None and Path(mat_file).is_file():
            mat_data = sio.loadmat(mat_file)
            rd = mat_data["RandDemand"]
            for q in range(self.dims.num_quarter):
                if rd.ndim == 2 and rd.shape[0] == 1:
                    self.rand_demand[q] = np.array(rd[0, q], dtype=float)
                else:
                    self.rand_demand[q] = np.array(rd[q], dtype=float)
            return self.rand_demand

        rng = np.random.default_rng(seed)
        real_size = int(self.config.num_scenario * 1.2)

        for q in range(self.dims.num_quarter):
            mean = self.demand.rv_mean[:, q, None]
            std = self.demand.rv_std[:, q, None]
            samples = rng.normal(loc=mean, scale=std, size=(self.dims.num_prod, real_size))
            # Truncate negative demand to zero
            samples = np.maximum(samples, 0.0)
            self.rand_demand[q] = samples

        if save_mat:
            mat_path = self.data.output_dir / "RandDemand.mat"
            cell_array = np.empty((1, self.dims.num_quarter), dtype=object)
            for q in range(self.dims.num_quarter):
                cell_array[0, q] = self.rand_demand[q]
            sio.savemat(str(mat_path), {"RandDemand": cell_array})

        return self.rand_demand

    def evaluate(
        self,
        mat_name: str,
        quarter_idx: int,
        keep_raw: bool = False,
    ) -> List[Any]:
        """Evaluates a qualification matrix over Monte Carlo demand scenarios for a given quarter.
        
        Args:
            mat_name: Key in self.qmat to evaluate.
            quarter_idx: 0-indexed quarter index.
            keep_raw: If True, saves individual scenario results in self.recordset.
            
        Returns:
            A progress row list matching the format in MATLAB.
        """
        if quarter_idx not in self.rand_demand:
            self.create_rand_demand()

        qmat = self.qmat[mat_name]
        demand_scenarios = self.rand_demand[quarter_idx]
        cap = self.capacity[:, quarter_idx]
        min_u = self.min_util

        n = self.dims.num_prod
        m = self.dims.num_site
        num_target = self.config.num_scenario

        sl_list: List[float] = []
        sl_prod_list: List[np.ndarray] = []
        ld_site_list: List[np.ndarray] = []
        obj_list: List[float] = []
        alloc_list: List[np.ndarray] = []

        scenario_idx = 0
        total_scenarios = demand_scenarios.shape[1]

        while len(sl_list) < num_target and scenario_idx < total_scenarios:
            d = demand_scenarios[:, scenario_idx]
            scenario_idx += 1

            sol = self.solver.solve(qmat, d, cap, min_u)
            if not sol.success:
                continue

            x_alloc = sol.x_matrix
            d_sum = np.sum(d)
            x_sum = np.sum(x_alloc)

            sl_val = float(x_sum / d_sum) if d_sum > 0 else 1.0
            prod_alloc = np.sum(x_alloc, axis=1)
            sl_prod = np.divide(prod_alloc, d, out=np.ones_like(d, dtype=float), where=(d > 0))
            ld_site = np.sum(x_alloc, axis=0)

            sl_list.append(sl_val)
            sl_prod_list.append(sl_prod)
            ld_site_list.append(ld_site)
            obj_list.append(sol.obj_value)
            alloc_list.append(x_alloc)

        if len(sl_list) < num_target:
            raise RuntimeError(
                f"Could only solve {len(sl_list)} / {num_target} scenarios for {mat_name} in quarter {quarter_idx}"
            )

        sl_arr = np.array(sl_list)
        sl_prod_arr = np.array(sl_prod_list).T  # Shape (n, num_target)
        ld_site_arr = np.array(ld_site_list).T  # Shape (m, num_target)
        obj_arr = np.array(obj_list)
        alloc_arr = np.array(alloc_list)         # Shape (num_target, n, m)

        # Calculate statistics
        sl_mean = float(np.mean(sl_arr))
        sl_p5 = float(np.percentile(sl_arr, 5))
        sl_p10 = float(np.percentile(sl_arr, 10))

        sl_prod_mean = np.mean(sl_prod_arr, axis=1)
        sl_prod_p5 = np.percentile(sl_prod_arr, 5, axis=1)
        sl_prod_p10 = np.percentile(sl_prod_arr, 10, axis=1)

        cap_safe = np.where(cap > 0, cap, 1.0)
        u_site_arr = ld_site_arr / cap_safe[:, None]
        u_site_mean = np.mean(u_site_arr, axis=1)
        u_site_p5 = np.percentile(u_site_arr, 5, axis=1)
        u_site_p10 = np.percentile(u_site_arr, 10, axis=1)

        obj_mean = float(np.mean(obj_arr))
        var_x_mean = np.mean(alloc_arr, axis=0)
        var_x_std = np.std(alloc_arr, axis=0)

        stat_record = {
            "SL": {"mean": sl_mean, "P5": sl_p5, "P10": sl_p10},
            "SL_prod": {"mean": sl_prod_mean, "P5": sl_prod_p5, "P10": sl_prod_p10},
            "U_site": {"mean": u_site_mean, "P5": u_site_p5, "P10": u_site_p10},
            "Obj_mean": obj_mean,
            "Var_x": {"mean": var_x_mean, "std": var_x_std},
        }
        self.stat[quarter_idx][mat_name] = stat_record

        if keep_raw:
            self.recordset[quarter_idx][mat_name] = {
                "SL": sl_arr,
                "SL_prod": sl_prod_arr,
                "Ld_Site": ld_site_arr,
                "Obj_Value": obj_arr,
            }

        num_links = int(np.sum(qmat))
        res_row = [
            mat_name,
            num_links,
            None,
            None,
            "",
            obj_mean,
            sl_mean,
            *[float(x) for x in u_site_mean],
            *[float(x) for x in u_site_p10],
            *[float(x) for x in u_site_p5],
        ]
        return res_row

    def check_options(self, ref_mat: np.ndarray) -> np.ndarray:
        """Finds all allowable primary and secondary links not currently active in ref_mat.
        
        Returns:
            np.ndarray of shape (num_available, 3) where columns are [prod_idx, site_idx, option_type].
        """
        active_links = set(map(tuple, np.argwhere(ref_mat > 0)))

        avail_primary = [
            (p, s, 1) for p, s in self.primary_options if (p, s) not in active_links
        ]
        avail_secondary = [
            (p, s, 2) for p, s in self.secondary_options if (p, s) not in active_links
        ]

        all_options = avail_primary + avail_secondary
        if not all_options:
            return np.empty((0, 3), dtype=int)
        return np.array(all_options, dtype=int)

    def the_next_best(self, mat_name: str, prior_best_obj: float) -> Tuple[List[Any], np.ndarray]:
        """Greedily tests each available link and selects the one with the highest objective mean."""
        ref_q = self.ref_quarter
        base_qmat = self.qmat[mat_name]
        options = self.check_options(base_qmat)

        if len(options) == 0:
            raise ValueError(f"No available links left to add from {mat_name}")

        results: List[List[Any]] = []
        obj_values: List[float] = []

        for i in range(len(options)):
            prod_ix, site_ix, opt_type = options[i]
            qmat_cand = base_qmat.copy()
            qmat_cand[prod_ix, site_ix] = 1.0

            self.qmat["temp"] = qmat_cand
            res = self.evaluate("temp", ref_q, keep_raw=False)
            obj_val = self.stat[ref_q]["temp"]["Obj_mean"]

            obj_values.append(obj_val)
            results.append(res)

        best_idx = int(np.argmax(obj_values))
        best_link_row = list(results[best_idx])
        best_opt = options[best_idx]

        best_link_row[2] = int(best_opt[0])  # prod_ix
        best_link_row[3] = int(best_opt[1])  # site_ix
        best_link_row[4] = int(best_opt[2])  # option type (1 or 2)

        qmat_next = base_qmat.copy()
        qmat_next[best_opt[0], best_opt[1]] = 1.0

        return best_link_row, qmat_next

    def clear_added_links(self) -> None:
        """Resets the progress table, stat, and qmat dictionaries by removing added links."""
        # Keep header row only
        if len(self.progress) > 1:
            self.progress = [self.progress[0]]

        # Remove 'link*' and 'proposed' from qmat and stat
        keys_to_remove = [k for k in self.qmat if k.startswith("link") or k in ("proposed", "temp")]
        for k in keys_to_remove:
            self.qmat.pop(k, None)

        for q in self.stat:
            for k in list(self.stat[q].keys()):
                if k.startswith("link") or k in ("proposed", "temp"):
                    self.stat[q].pop(k, None)

    def optimize(
        self,
        ref_quarter: Optional[int] = None,
        keep_raw_ref: bool = False,
        keep_raw_links: bool = False,
    ) -> None:
        """Executes the iterative greedy qualification optimization starting from 'base'.
        
        Args:
            ref_quarter: 1-indexed or 0-indexed reference quarter. If 1 <= ref_quarter <= num_quarters,
                         it is converted to 0-indexed automatically.
            keep_raw_ref: Whether to keep raw simulation datasets for ref quarter.
            keep_raw_links: Whether to keep raw simulation datasets for added links.
        """
        if ref_quarter is not None:
            # Handle 1-indexed input from MATLAB convention
            if 1 <= ref_quarter <= self.dims.num_quarter:
                self.ref_quarter = ref_quarter - 1
            else:
                self.ref_quarter = ref_quarter

        self.clear_added_links()
        q_ref = self.ref_quarter

        # Evaluate base, plan, max benchmarks
        rs_base = self.evaluate("base", q_ref, keep_raw=keep_raw_ref)
        self.progress.append(rs_base)

        rs_plan = self.evaluate("plan", q_ref, keep_raw=keep_raw_ref)
        self.progress.append(rs_plan)

        rs_max = self.evaluate("max", q_ref, keep_raw=keep_raw_ref)
        self.progress.append(rs_max)
        sl_max = rs_max[6]

        current_best_obj = rs_base[5]
        current_best_sl = rs_base[6]

        sl_target = self.config.sl_target if self.config.sl_target > 0 else sl_max
        tol = self.config.sl_tol

        round_num = 0
        max_allowed_rounds = min(self.dims.num_option, self.config.max_round)

        while (
            (current_best_sl + tol < sl_target)
            and (current_best_sl + tol < sl_max * self.config.pct_of_sl_full_target)
            and (round_num < max_allowed_rounds)
        ):
            ref_mat_name = "base" if round_num == 0 else f"link{round_num}"
            best_link, qmat_next = self.the_next_best(ref_mat_name, current_best_obj)

            added_name = f"link{round_num + 1}"
            self.qmat[added_name] = qmat_next

            # Re-evaluate added link
            self.evaluate(added_name, q_ref, keep_raw=keep_raw_links)
            best_link[0] = added_name
            self.progress.append(best_link)

            current_best_obj = best_link[5]
            current_best_sl = best_link[6]
            round_num += 1

    def testify_proposed_matrix(
        self,
        proposed_mat_name: Optional[str] = None,
        keep_raw: bool = False,
    ) -> str:
        """Evaluates base, plan, max, and the proposed network across all non-reference quarters.
        
        Args:
            proposed_mat_name: Specific matrix key to propose (defaults to highest added link).
            keep_raw: Whether to preserve raw Monte Carlo simulation outputs.
            
        Returns:
            Name of the proposed matrix.
        """
        if proposed_mat_name is None:
            # Pick highest added link
            link_keys = [k for k in self.qmat if k.startswith("link")]
            if link_keys:
                link_nums = [int(k.replace("link", "")) for k in link_keys]
                proposed_mat_name = f"link{max(link_nums)}"
            else:
                proposed_mat_name = "plan"

        self.qmat["proposed"] = self.qmat[proposed_mat_name].copy()
        self.stat[self.ref_quarter]["proposed"] = self.stat[self.ref_quarter][proposed_mat_name]

        # Update name in progress table for the chosen proposed link
        for r in range(1, len(self.progress)):
            if self.progress[r][0] == proposed_mat_name:
                self.progress[r][0] = "proposed"

        # Evaluate across all other quarters
        matrices_to_test = ["base", "plan", "max", "proposed"]
        for q in range(self.dims.num_quarter):
            if q == self.ref_quarter:
                continue
            for mat_name in matrices_to_test:
                self.evaluate(mat_name, q, keep_raw=keep_raw)

        return proposed_mat_name

    def observe_loading(
        self,
        mat_name: str,
        quarter_idx: int,
        cov: float = 0.3,
        export: bool = False,
    ) -> Dict[str, np.ndarray]:
        """Evaluates production allocation under unbiased mean, high (+cov), and low (-cov) demand."""
        # Convert 1-indexed quarter if necessary
        if 1 <= quarter_idx <= self.dims.num_quarter:
            q = quarter_idx - 1
        else:
            q = quarter_idx

        qmat = self.qmat[mat_name]
        avg_demand = self.demand.rv_mean[:, q]
        high_demand = avg_demand * (1.0 + cov)
        low_demand = np.maximum(avg_demand * (1.0 - cov), 0.0)

        cap = self.capacity[:, q]
        min_u = self.min_util

        scenarios = {
            "average": avg_demand,
            "high": high_demand,
            "low": low_demand,
        }
        loading_dict: Dict[str, np.ndarray] = {}

        for scenario_name, d_vec in scenarios.items():
            sol = self.solver.solve(qmat, d_vec, cap, min_u)
            loading_dict[scenario_name] = sol.x_matrix

        if export:
            out_file = self.data.output_dir / f"loading_{mat_name}.xlsx"
            with pd.ExcelWriter(out_file, engine="openpyxl") as writer:
                for scenario_name, alloc_mat in loading_dict.items():
                    df = pd.DataFrame(
                        alloc_mat,
                        index=self.basic_info.products,
                        columns=self.basic_info.sites,
                    )
                    df.to_excel(writer, sheet_name=scenario_name)

        return loading_dict

    def result_export(
        self,
        output_dir: Optional[Union[str, Path]] = None,
        filename: str = "Outputs.xlsx",
    ) -> Path:
        """Exports the complete simulation results into Outputs.xlsx."""
        out_dir = self.data.output_dir if output_dir is None else Path(output_dir)
        target_path = out_dir / filename

        # Convert product and site index in progress table to names
        formatted_progress: List[List[Any]] = [list(self.progress[0])]
        for row in self.progress[1:]:
            new_row = list(row)
            prod_val = new_row[2]
            site_val = new_row[3]

            if prod_val is not None and prod_val != "":
                if isinstance(prod_val, (int, np.integer)) and 0 <= prod_val < len(self.basic_info.products):
                    new_row[2] = self.basic_info.products[prod_val]
            else:
                new_row[2] = ""

            if site_val is not None and site_val != "":
                if isinstance(site_val, (int, np.integer)) and 0 <= site_val < len(self.basic_info.sites):
                    new_row[3] = self.basic_info.sites[site_val]
            else:
                new_row[3] = ""

            formatted_progress.append(new_row)

        proposed_mat = self.qmat.get("proposed", self.qmat["base"])
        return export_results_to_excel(
            output_path=target_path,
            progress_rows=formatted_progress,
            basic_info=self.basic_info,
            stat_by_quarter=self.stat,
            proposed_qmat=proposed_mat,
            proposed_mat_name="proposed",
        )
