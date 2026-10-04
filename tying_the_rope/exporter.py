"""Export module for dumping optimization metrics and loading tables to Excel."""

from pathlib import Path
from typing import Any, Dict, List, Union
import numpy as np
import pandas as pd


def export_results_to_excel(
    output_path: Union[str, Path],
    progress_rows: List[List[Any]],
    basic_info,
    stat_by_quarter: Dict[int, Dict[str, Any]],
    proposed_qmat: np.ndarray,
    proposed_mat_name: str = "proposed",
) -> Path:
    """Exports all optimization results to an Excel workbook (e.g. py_Outputs.xlsx).
    
    Args:
        output_path: Destination .xlsx file path.
        progress_rows: Rows of LinkAddProgress (including headers and link progression).
        basic_info: BasicInfo instance with product, site, and quarter lists.
        stat_by_quarter: Nested dictionary mapping quarter index -> matrix name -> evaluation stats.
        proposed_qmat: Final binary qualification matrix of shape (n, m).
        proposed_mat_name: Name of the proposed matrix to export metrics for.
        
    Returns:
        Path to the saved Excel file.
    """
    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    products = basic_info.products
    sites = basic_info.sites
    quarters = basic_info.quarters
    num_prod = len(products)
    num_site = len(sites)
    num_quarters = len(quarters)

    with pd.ExcelWriter(out_file, engine="openpyxl") as writer:
        # Sheet 1: LinkAddProgress
        df_progress = pd.DataFrame(progress_rows[1:], columns=progress_rows[0])
        df_progress.to_excel(writer, sheet_name="LinkAddProgress", index=False)

        # Sheet 2: Metrics under Recomended Qual
        metrics_rows = []
        # Header row: ['', '', '', '', q1, q2, ...]
        metrics_headers = ["", "", "", ""] + quarters

        # Overall SL
        overall_sl = ["", "", "Overall SL", ""] + [
            stat_by_quarter[q][proposed_mat_name]["SL"]["mean"] for q in range(num_quarters)
        ]
        metrics_rows.append(overall_sl)

        # Product SL
        for i, prod in enumerate(products):
            p_sl = ["Product SL", prod, "", ""] + [
                stat_by_quarter[q][proposed_mat_name]["SL_prod"]["mean"][i] for q in range(num_quarters)
            ]
            metrics_rows.append(p_sl)

        # Expected Site Utilization
        for j, site in enumerate(sites):
            u_mean = ["Expected Site Utilization", site, "", ""] + [
                stat_by_quarter[q][proposed_mat_name]["U_site"]["mean"][j] for q in range(num_quarters)
            ]
            metrics_rows.append(u_mean)

        # P10 Site Utilization
        for j, site in enumerate(sites):
            u_p10 = ["P10 of Site Utilization", site, "", ""] + [
                stat_by_quarter[q][proposed_mat_name]["U_site"]["P10"][j] for q in range(num_quarters)
            ]
            metrics_rows.append(u_p10)

        df_metrics = pd.DataFrame(metrics_rows, columns=metrics_headers)
        df_metrics.to_excel(writer, sheet_name="Metrics under Recomended Qual", index=False)

        # Sheet 3: Expected Loading
        loading_rows = []
        for q in range(num_quarters):
            quarter_name = quarters[q]
            header = [quarter_name] + sites
            loading_rows.append(header)
            mean_alloc = stat_by_quarter[q][proposed_mat_name]["Var_x"]["mean"]  # (n, m)
            for i, prod in enumerate(products):
                prod_row = [prod] + [float(mean_alloc[i, j]) for j in range(num_site)]
                loading_rows.append(prod_row)
            # Empty separator row
            loading_rows.append([""] * (num_site + 1))

        df_loading = pd.DataFrame(loading_rows)
        df_loading.to_excel(writer, sheet_name="Expected Loading", header=False, index=False)

        # Sheet 4: Qual matrix
        df_qmat = pd.DataFrame(
            proposed_qmat,
            index=products,
            columns=sites,
        )
        df_qmat.to_excel(writer, sheet_name="Qual matrix")

    return out_file

