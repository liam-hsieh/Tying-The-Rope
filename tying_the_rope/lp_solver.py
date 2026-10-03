"""Linear and Mixed-Integer Programming solver for Tying-The-Rope using SciPy."""

from dataclasses import dataclass
from typing import Optional, Tuple
import numpy as np
from scipy.optimize import LinearConstraint, linprog, milp


@dataclass
class LPSolution:
    """Results returned from solving an LP or MIP instance."""
    success: bool
    obj_value: float          # Maximized objective value
    x_matrix: np.ndarray       # Shape (n, m): production allocation
    u_slack: np.ndarray        # Shape (m,): site minimum utilization shortfall
    y_open: Optional[np.ndarray] = None  # Shape (m,): site open/close indicator (MIP only)
    message: str = ""


class LPSolver:
    """Prepares and solves optimization problems for given demand scenarios."""

    def __init__(
        self,
        num_prod: int,
        num_site: int,
        margin: np.ndarray,
        cost_matrix: np.ndarray,
        wt_min_u_obj: float = 0.2,
        big_m: float = 1000.0,
        mode: str = "LP",
    ):
        self.n = num_prod
        self.m = num_site
        self.margin = margin
        self.cost_matrix = cost_matrix
        self.wt_min_u = wt_min_u_obj
        self.big_m = big_m
        self.mode = mode.upper()

        # Profit coefficients per (product, site) pair: (n, m)
        # Margin is (n,), broadcast over m sites
        self.profit_matrix = self.margin[:, None] - self.cost_matrix
        self.profit_flat = self.profit_matrix.flatten()

    def solve(
        self,
        qmat: np.ndarray,
        demand: np.ndarray,
        capacity: np.ndarray,
        min_util: np.ndarray,
    ) -> LPSolution:
        """Solves LP or MIP for a single demand scenario.
        
        Args:
            qmat: Binary qualification matrix of shape (n, m).
            demand: Demand scenario vector of shape (n,).
            capacity: Site capacity vector of shape (m,).
            min_util: Site minimum utilization fraction of shape (m,).
            
        Returns:
            LPSolution containing status, maximized objective, and decision variables.
        """
        min_loads = min_util * capacity

        if self.mode == "MIP":
            return self._solve_mip(qmat, demand, capacity, min_loads)
        else:
            return self._solve_lp(qmat, demand, capacity, min_loads)

    def _solve_lp(
        self,
        qmat: np.ndarray,
        demand: np.ndarray,
        capacity: np.ndarray,
        min_loads: np.ndarray,
    ) -> LPSolution:
        n, m = self.n, self.m
        num_vars = n * m + m

        # linprog minimizes c^T z:
        # z[:n*m] = x, z[n*m:] = u
        c = np.empty(num_vars, dtype=float)
        c[: n * m] = -self.profit_flat
        c[n * m :] = self.wt_min_u

        # Build inequality constraints A_ub @ z <= b_ub
        # 1) Product demand upper bound: sum_j x_{ij} <= demand_i (n rows)
        # 2) Site capacity upper bound: sum_i x_{ij} <= capacity_j (m rows)
        # 3) Minimum utilization shortfall: sum_i x_{ij} + u_j >= min_loads_j
        #    <=> -sum_i x_{ij} - u_j <= -min_loads_j (m rows)
        num_rows = n + 2 * m
        A_ub = np.zeros((num_rows, num_vars), dtype=float)
        b_ub = np.zeros(num_rows, dtype=float)

        # 1) sum_j x_{ij} <= demand_i
        for i in range(n):
            A_ub[i, i * m : (i + 1) * m] = 1.0
            b_ub[i] = demand[i]

        # 2) sum_i x_{ij} <= capacity_j
        for j in range(m):
            row_idx = n + j
            A_ub[row_idx, j :: m] = 1.0
            b_ub[row_idx] = capacity[j]

        # 3) -sum_i x_{ij} - u_j <= -min_loads_j
        for j in range(m):
            row_idx = n + m + j
            A_ub[row_idx, j :: m] = -1.0
            A_ub[row_idx, n * m + j] = -1.0
            b_ub[row_idx] = -min_loads[j]

        # Variable bounds
        # x_ij in [0, 999] if qualified else [0, 0]
        # u_j in [0, 999]
        q_flat = qmat.flatten()
        lb = np.zeros(num_vars, dtype=float)
        ub = np.zeros(num_vars, dtype=float)
        ub[: n * m] = np.where(q_flat > 0, 999.0, 0.0)
        ub[n * m :] = 999.0
        bounds = list(zip(lb, ub))

        res = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method="highs")

        if not res.success:
            return LPSolution(
                success=False,
                obj_value=0.0,
                x_matrix=np.zeros((n, m)),
                u_slack=np.zeros(m),
                message=res.message,
            )

        x_alloc = res.x[: n * m].reshape((n, m))
        u_val = res.x[n * m :]
        max_obj = -float(res.fun)

        return LPSolution(
            success=True,
            obj_value=max_obj,
            x_matrix=x_alloc,
            u_slack=u_val,
            message="Optimization terminated successfully.",
        )

    def _solve_mip(
        self,
        qmat: np.ndarray,
        demand: np.ndarray,
        capacity: np.ndarray,
        min_loads: np.ndarray,
    ) -> LPSolution:
        n, m = self.n, self.m
        num_vars = n * m + 2 * m  # x (n*m), y (m), u (m)

        c = np.empty(num_vars, dtype=float)
        c[: n * m] = -self.profit_flat
        c[n * m : n * m + m] = 0.0       # y
        c[n * m + m :] = self.wt_min_u   # u

        # Constraints:
        # 1) sum_j x_{ij} <= demand_i (n rows)
        # 2) sum_i x_{ij} <= capacity_j (m rows)
        # 3) -sum_i x_{ij} - bigM * y_j <= -min_loads_j (m rows)
        # 4) -sum_i x_{ij} + bigM * y_j - u_j <= bigM - min_loads_j (m rows)
        num_rows = n + 3 * m
        A_ub = np.zeros((num_rows, num_vars), dtype=float)
        b_ub = np.zeros(num_rows, dtype=float)

        for i in range(n):
            A_ub[i, i * m : (i + 1) * m] = 1.0
            b_ub[i] = demand[i]

        for j in range(m):
            A_ub[n + j, j :: m] = 1.0
            b_ub[n + j] = capacity[j]

        for j in range(m):
            row_idx = n + m + j
            A_ub[row_idx, j :: m] = -1.0
            A_ub[row_idx, n * m + j] = -self.big_m
            b_ub[row_idx] = -min_loads[j]

        for j in range(m):
            row_idx = n + 2 * m + j
            A_ub[row_idx, j :: m] = -1.0
            A_ub[row_idx, n * m + j] = self.big_m
            A_ub[row_idx, n * m + m + j] = -1.0
            b_ub[row_idx] = self.big_m - min_loads[j]

        q_flat = qmat.flatten()
        lb = np.zeros(num_vars, dtype=float)
        ub = np.zeros(num_vars, dtype=float)
        ub[: n * m] = np.where(q_flat > 0, 999.0, 0.0)
        ub[n * m : n * m + m] = 1.0
        ub[n * m + m :] = capacity

        integrality = np.zeros(num_vars, dtype=int)
        integrality[n * m : n * m + m] = 1  # y variables are binary integer

        constraints = LinearConstraint(A_ub, -np.inf, b_ub)
        bounds = (lb, ub)

        res = milp(c=c, integrality=integrality, bounds=bounds, constraints=constraints)

        if not res.success:
            return LPSolution(
                success=False,
                obj_value=0.0,
                x_matrix=np.zeros((n, m)),
                u_slack=np.zeros(m),
                message=res.message,
            )

        x_alloc = res.x[: n * m].reshape((n, m))
        y_val = res.x[n * m : n * m + m]
        u_val = res.x[n * m + m :]
        max_obj = -float(res.fun)

        return LPSolution(
            success=True,
            obj_value=max_obj,
            x_matrix=x_alloc,
            u_slack=u_val,
            y_open=y_val,
            message="Optimization terminated successfully.",
        )

