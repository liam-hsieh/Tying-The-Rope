# Tying-The-Rope

Site-product qualification and selection optimization engine.

`Tying-The-Rope` simulates and optimizes multi-site manufacturing qualification networks under demand uncertainty using Monte Carlo simulation, Linear Programming (LP), and Mixed-Integer Programming (MIP).

---

## Features

- **End-to-End Qualification Optimization**: Iteratively identifies and evaluates the most effective qualification links to maximize profit and service level (SL) while honoring capacity constraints and minimum site utilization targets.
- **Monte Carlo Simulation**: Evaluates qualification performance across stochastic demand scenarios with forecast error distributions.
- **LP & MIP Solvers via SciPy / HiGHS**: High-performance optimization backend powered by SciPy and the C++ HiGHS solver.
- **Comprehensive Excel Reporting**: Outputs full progress logs, service level percentiles (Mean, P10, P5), expected loading schedules, and final qualification matrices to Excel.
- **Modern Python Architecture**: Type hints, dataclasses, automated testing via `pytest`, and packaged with standard `pyproject.toml`.

---

## Documentation

For a detailed walkthrough of the manufacturing flexibility problem, mathematical formulation, input parameters, and how to use the simulation outputs for business decisions, see:
- 📖 **[Problem Formulation & Decision Framework](docs/PROBLEM_DESCRIPTION.md)**

---

## Project Structure

```
Tying-The-Rope/
├── docs/
│   └── PROBLEM_DESCRIPTION.md   # Problem formulation & decision guide
├── main.py                     # CLI entry point and execution script
├── pyproject.toml              # Modern PEP 621 package metadata & dependencies
├── requirements.txt            # Dependency specification
├── Inputs/
│   └── examples.xlsx           # Input problem definition & configuration sheets
├── outputs/                    # Output directory for simulation results
│   └── examples/
│       ├── py_Outputs.xlsx     # Generated metrics, loading schedules, and progress (py_ prefix)
│       └── py_RandDemand.mat   # Monte Carlo demand scenarios (py_ prefix)
├── tying_the_rope/             # Core Python package
│   ├── __init__.py             # Public API exports
│   ├── config.py               # Model configuration dataclass
│   ├── data_loader.py          # Excel workbook ingestion & preprocessing
│   ├── lp_solver.py            # Linear and mixed-integer programming solver
│   ├── exporter.py             # Excel reporting engine
│   └── model.py                # Main TyingTheRope simulation & optimization class
├── tests/
│   └── test_model.py           # Automated unit and integration tests
└── README.md                   # Project documentation
```

---

## Installation

### Prerequisites
- Python 3.10 or higher
- Optional: [`uv`](https://github.com/astral-sh/uv) (recommended) or standard `pip`

### Install Dependencies

Using `pip`:
```bash
pip install -r requirements.txt
pip install -e .
```

Or using `uv`:
```bash
uv sync
```

---

## Usage

### 1. Command Line Interface (CLI)

Run optimization using the default settings (`Inputs/examples.xlsx`, reference quarter 2, 100 scenarios):
```bash
python main.py
```

Or with custom parameters:
```bash
python main.py --input Inputs/examples.xlsx --ref-quarter 2 --max-round 10 --num-scenario 50 --mode LP
```

Available CLI arguments:
- `--input, -i`: Path to the input Excel workbook (default: `Inputs/examples.xlsx`).
- `--sl-target`: Service level target to terminate optimization early (default: `0.0` for full potential).
- `--max-round`: Maximum number of qualification links to add (default: `20`).
- `--num-scenario`: Number of Monte Carlo demand scenarios per quarter (default: `100`).
- `--ref-quarter`: Reference quarter for recommendation (1-indexed, default: `2`).
- `--mode`: Solver mode: `LP` or `MIP` (default: `LP`).
- `--seed`: Random seed for demand scenario sampling (default: `42`).
- `--observe-loading`: Export deterministic loading scenarios for average, high, and low demand.

---

### 2. Python API

```python
from tying_the_rope import ModelConfig, TyingTheRope

# Configure model options
config = ModelConfig(
    sl_target=0.0,
    max_round=15,
    num_scenario=100,
    mode="LP",
)

# Initialize engine
ttr = TyingTheRope("Inputs/examples.xlsx", config=config)

# Generate stochastic demand scenarios
ttr.create_rand_demand(seed=42)

# Run greedy qualification optimization
ttr.optimize(ref_quarter=2)

# Testify proposed qualification network across all quarters
ttr.testify_proposed_matrix()

# Export comprehensive report to Excel (prefixed with py_ to preserve original)
output_path = ttr.result_export(filename="py_Outputs.xlsx")
print(f"Results exported to {output_path}")
```

---

## Testing

Run the test suite with `pytest`:

```bash
pytest
```
Or with `uv`:
```bash
uv run pytest
```

---

## Migration from MATLAB

This repository was migrated from MATLAB to Python:
- MATLAB's `@Tying_The_Rope` object-oriented structure has been refactored into the modular Python package `tying_the_rope/`.
- Linprog calls were ported to `scipy.optimize.linprog(method="highs")` and `scipy.optimize.milp` with substantial performance gains.
- Monte Carlo simulation logic preserves exact truncated-normal sampling and percentile tracking ($P5, P10$, mean).
- Python output files use the `py_` prefix (`py_Outputs.xlsx` and `py_RandDemand.mat`) so the original MATLAB output files remain untouched.

