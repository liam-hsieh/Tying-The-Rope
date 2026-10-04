"""Unit and integration tests for TyingTheRope Python implementation."""

from pathlib import Path
import numpy as np
import openpyxl
import pytest

from tying_the_rope import ModelConfig, TyingTheRope, load_input_file
from tying_the_rope.lp_solver import LPSolver


INPUT_FILE = Path("Inputs/examples.xlsx")


def test_data_loader():
    """Test loading input data from Excel."""
    dataset = load_input_file(INPUT_FILE)
    assert len(dataset.basic_info.products) == 11
    assert len(dataset.basic_info.sites) == 9
    assert len(dataset.basic_info.quarters) == 8

    assert dataset.qmat["base"].shape == (11, 9)
    assert dataset.qmat["plan"].shape == (11, 9)
    assert dataset.qmat["max"].shape == (11, 9)
    assert dataset.qmat["exclusion"].shape == (11, 9)

    assert dataset.demand.fcst.shape == (11, 8)
    assert dataset.demand.margin.shape == (11,)
    assert dataset.capacity.shape == (9, 8)
    assert dataset.min_util.shape == (9,)
    assert dataset.dims.num_option > 0


def test_lp_solver_constraints():
    """Test that LPSolver respects capacity, demand, and qualification bounds."""
    dataset = load_input_file(INPUT_FILE)
    solver = LPSolver(
        num_prod=dataset.dims.num_prod,
        num_site=dataset.dims.num_site,
        margin=dataset.demand.margin,
        cost_matrix=dataset.cost_matrix,
        mode="LP",
    )

    q = 0
    qmat = dataset.qmat["base"]
    demand = dataset.demand.rv_mean[:, q]
    cap = dataset.capacity[:, q]
    min_u = dataset.min_util

    sol = solver.solve(qmat, demand, cap, min_u)
    assert sol.success is True
    assert sol.obj_value > 0

    x = sol.x_matrix
    # Demand upper bound
    assert np.all(np.sum(x, axis=1) <= demand + 1e-6)

    # Capacity upper bound
    assert np.all(np.sum(x, axis=0) <= cap + 1e-6)

    # Qualification limit: where qmat == 0, x must be 0
    unqualified = (qmat == 0)
    assert np.all(np.abs(x[unqualified]) < 1e-6)


def test_check_options():
    """Test finding available primary and secondary links."""
    ttr = TyingTheRope(input_file=INPUT_FILE)
    options = ttr.check_options(ttr.qmat["base"])
    assert len(options) > 0

    # Ensure no already active links are proposed
    base = ttr.qmat["base"]
    for row in options:
        prod_idx, site_idx, opt_type = row
        assert base[prod_idx, site_idx] == 0
        assert opt_type in (1, 2)


def test_end_to_end_optimization(tmp_path):
    """Test end-to-end simulation, greedy optimization, and result export."""
    config = ModelConfig(
        sl_target=0.0,
        max_round=3,       # Small round for fast testing
        num_scenario=20,   # Small scenario count for fast testing
    )
    ttr = TyingTheRope(
        input_file=INPUT_FILE,
        config=config,
        output_dir=tmp_path,
    )

    # Step 1: Create random demand and verify py_RandDemand.mat
    ttr.create_rand_demand(seed=123, save_mat=True)
    assert len(ttr.rand_demand) == 8
    expected_mat = tmp_path / ttr.data.version_name / "py_RandDemand.mat"
    assert expected_mat.is_file()

    # Step 2: Optimize on reference quarter (using quarter index 2)
    ttr.optimize(ref_quarter=2)
    assert len(ttr.progress) >= 4  # header + base + plan + max + at least 1 link

    # Step 3: Testify proposed matrix
    proposed_name = ttr.testify_proposed_matrix()
    assert "proposed" in ttr.qmat
    assert proposed_name.startswith("link")

    # Step 4: Export results and verify default py_Outputs.xlsx
    out_file = ttr.result_export(output_dir=tmp_path)
    assert out_file.name == "py_Outputs.xlsx"
    assert out_file.is_file()

    # Step 5: Verify exported workbook sheets
    wb = openpyxl.load_workbook(out_file)
    expected_sheets = {
        "LinkAddProgress",
        "Metrics under Recomended Qual",
        "Expected Loading",
        "Qual matrix",
    }
    assert expected_sheets.issubset(set(wb.sheetnames))

