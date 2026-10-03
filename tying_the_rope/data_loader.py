"""Data loading and preprocessing module for Tying-The-Rope."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Union
import numpy as np
import pandas as pd


@dataclass
class BasicInfo:
    """Basic metadata describing products, sites, and quarters."""
    products: List[str]
    sites: List[str]
    quarters: List[str]


@dataclass
class DemandData:
    """Demand parameters and forecast quantities."""
    fcst: np.ndarray        # Shape (n, num_quarters): raw forecast mean
    bias: np.ndarray        # Shape (n, num_quarters): forecast bias
    rv_mean: np.ndarray     # Shape (n, num_quarters): unbiased mean (rv_mean = fcst - bias)
    rv_std: np.ndarray      # Shape (n, num_quarters): standard deviation of forecast error
    margin: np.ndarray      # Shape (n,): demand margin per product


@dataclass
class ProblemDimensions:
    """Problem dimension counters."""
    num_prod: int
    num_site: int
    num_quarter: int
    num_option: int


@dataclass
class InputDataSet:
    """Container holding all parsed input datasets from Excel."""
    basic_info: BasicInfo
    dims: ProblemDimensions
    qmat: Dict[str, np.ndarray]  # Keys: 'base', 'plan', 'max', 'exclusion'
    demand: DemandData
    capacity: np.ndarray         # Shape (num_site, num_quarter)
    min_util: np.ndarray         # Shape (num_site,)
    priority_weight: np.ndarray  # Shape (num_prod, num_site)
    cost_matrix: np.ndarray      # Shape (num_prod, num_site)
    input_file_path: Path
    version_name: str
    output_dir: Path


def load_input_file(input_path: Union[str, Path], output_base_dir: Union[str, Path] = "outputs") -> InputDataSet:
    """Loads all matrices and sheets from the specified Excel workbook.
    
    Args:
        input_path: Path to the input Excel file (e.g. 'Inputs/examples.xlsx').
        output_base_dir: Base directory where output directories will be created.
        
    Returns:
        InputDataSet instance populated with all data.
    """
    path = Path(input_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Input file not found at: {path}")

    version_name = path.stem
    output_dir = Path(output_base_dir) / version_name
    output_dir.mkdir(parents=True, exist_ok=True)

    # Read BasicInfo sheet (no header)
    df_basic = pd.read_excel(path, sheet_name="BasicInfo", header=None)
    products = [str(x).strip() for x in df_basic.iloc[:, 0].dropna()]
    sites = [str(x).strip() for x in df_basic.iloc[:, 1].dropna()]
    quarters = [str(x).strip() for x in df_basic.iloc[:, 2].dropna()]

    n = len(products)
    m = len(sites)
    num_quarters = len(quarters)

    # Read Priority and Cost matrices
    df_priority = pd.read_excel(path, sheet_name="Priority", header=None)
    df_cost = pd.read_excel(path, sheet_name="Cost", header=None)
    priority_weight = df_priority.to_numpy(dtype=float)
    cost_matrix = df_cost.to_numpy(dtype=float)

    # Read Demand sheet
    df_demand = pd.read_excel(path, sheet_name="Demand", header=None)
    sht_demand = df_demand.to_numpy(dtype=float)
    if sht_demand.shape[0] != n:
        raise ValueError(f"Demand sheet row count ({sht_demand.shape[0]}) does not match product count ({n})")

    # Read Site sheet
    df_site = pd.read_excel(path, sheet_name="Site", header=None)
    sht_site = df_site.to_numpy(dtype=float)
    if sht_site.shape[0] != m:
        raise ValueError(f"Site sheet row count ({sht_site.shape[0]}) does not match site count ({m})")

    # Read Qualification matrices
    qmat_base = pd.read_excel(path, sheet_name="BaseQual", header=None).to_numpy(dtype=float)
    qmat_plan = pd.read_excel(path, sheet_name="PlanQual", header=None).to_numpy(dtype=float)
    qmat_max = pd.read_excel(path, sheet_name="MaxQual", header=None).to_numpy(dtype=float)
    rmat = pd.read_excel(path, sheet_name="Exclusions", header=None).to_numpy(dtype=float)

    expected_shape = (n, m)
    for name, mat in [("BaseQual", qmat_base), ("PlanQual", qmat_plan), ("MaxQual", qmat_max), ("Exclusions", rmat)]:
        if mat.shape != expected_shape:
            raise ValueError(f"{name} shape {mat.shape} does not match expected (products={n}, sites={m})")

    qmat = {
        "base": qmat_base,
        "plan": qmat_plan,
        "max": qmat_max,
        "exclusion": rmat,
    }

    # Number of allowable options (0 for primary, 2 for secondary)
    num_options = int(np.sum(rmat == 0) + np.sum(rmat == 2))

    dims = ProblemDimensions(
        num_prod=n,
        num_site=m,
        num_quarter=num_quarters,
        num_option=num_options,
    )

    # Process Demand parameters
    # Col 0: forecast bias coeff; Col 1: error std coeff; Col 2: margin; Col 3..: forecast mean per quarter
    d_mu = sht_demand[:, 3 : 3 + num_quarters]
    bias_coeff = sht_demand[:, 0:1]
    sig_coeff = sht_demand[:, 1:2]
    d_bias = d_mu * bias_coeff
    d_mu_adj = d_mu - d_bias
    d_sig = d_mu * sig_coeff
    margin = sht_demand[:, 2]

    demand_data = DemandData(
        fcst=d_mu,
        bias=d_bias,
        rv_mean=d_mu_adj,
        rv_std=d_sig,
        margin=margin,
    )

    # Process Site parameters
    # Col 0: MinUtil; Col 1..: Capacity per quarter
    min_util = sht_site[:, 0]
    capacity = sht_site[:, 1 : 1 + num_quarters]

    basic_info = BasicInfo(
        products=products,
        sites=sites,
        quarters=quarters,
    )

    return InputDataSet(
        basic_info=basic_info,
        dims=dims,
        qmat=qmat,
        demand=demand_data,
        capacity=capacity,
        min_util=min_util,
        priority_weight=priority_weight,
        cost_matrix=cost_matrix,
        input_file_path=path,
        version_name=version_name,
        output_dir=output_dir,
    )

