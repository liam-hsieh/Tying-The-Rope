"""Main entry point for running Tying-The-Rope optimization."""

import argparse
import sys
import time
from pathlib import Path

from tying_the_rope import ModelConfig, TyingTheRope


def main():
    parser = argparse.ArgumentParser(
        description="Tying-The-Rope: Site-Product Selection and Qualification Optimization"
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default="Inputs/examples.xlsx",
        help="Path to input Excel workbook (default: Inputs/examples.xlsx)",
    )
    parser.add_argument(
        "--sl-target",
        type=float,
        default=0.0,
        help="Target overall service level (default: 0.0 for full potential)",
    )
    parser.add_argument(
        "--max-round",
        type=int,
        default=20,
        help="Maximum rounds of qualification links to add (default: 20)",
    )
    parser.add_argument(
        "--num-scenario",
        type=int,
        default=100,
        help="Number of Monte Carlo demand scenarios (default: 100)",
    )
    parser.add_argument(
        "--ref-quarter",
        type=int,
        default=2,
        help="Reference quarter index for link recommendation (1-indexed, default: 2)",
    )
    parser.add_argument(
        "--mode",
        choices=["LP", "MIP"],
        default="LP",
        help="Optimization solver mode: LP or MIP (default: LP)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for demand generation (default: 42)",
    )
    parser.add_argument(
        "--observe-loading",
        action="store_true",
        help="Also evaluate and export loadings for average, high, and low scenarios",
    )

    args = parser.parse_args()

    start_time = time.time()
    print("=" * 60)
    print("  Tying-The-Rope: Site-Product Qualification Optimization")
    print("=" * 60)
    print(f"Input file:     {args.input}")
    print(f"SL Target:      {args.sl_target}")
    print(f"Max rounds:     {args.max_round}")
    print(f"Scenarios:      {args.num_scenario}")
    print(f"Ref Quarter:    {args.ref_quarter}")
    print(f"Mode:           {args.mode}")
    print("-" * 60)

    config = ModelConfig(
        mode=args.mode,
        sl_target=args.sl_target,
        max_round=args.max_round,
        num_scenario=args.num_scenario,
    )

    ttr = TyingTheRope(
        input_file=args.input,
        config=config,
    )

    print(f"Loaded dataset: {ttr.data.version_name}")
    print(f"  Products: {len(ttr.basic_info.products)}")
    print(f"  Sites:    {len(ttr.basic_info.sites)}")
    print(f"  Quarters: {len(ttr.basic_info.quarters)}")
    print(f"  Allowable qualification options: {ttr.dims.num_option}")

    print("\n[1/4] Generating Monte Carlo demand scenarios...")
    ttr.create_rand_demand(seed=args.seed)

    print(f"\n[2/4] Optimizing qualification network on quarter {args.ref_quarter}...")
    ttr.optimize(ref_quarter=args.ref_quarter)

    print("\n[3/4] Testifying proposed matrix across all quarters...")
    proposed_name = ttr.testify_proposed_matrix()
    print(f"  Selected proposed network: {proposed_name}")

    print("\n[4/4] Exporting simulation results to Excel...")
    out_file = ttr.result_export()
    print(f"  Saved outputs to: {out_file}")

    if args.observe_loading:
        print("\nEvaluating and exporting loading scenarios...")
        ttr.observe_loading(mat_name="plan", quarter_idx=4, cov=0.3, export=True)
        print("  Exported loading matrices.")

    elapsed = time.time() - start_time
    print("-" * 60)
    print(f"Completed in {elapsed:.2f} seconds.")
    print("=" * 60)


if __name__ == "__main__":
    main()

