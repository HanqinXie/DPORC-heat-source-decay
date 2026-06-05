from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent

DEFAULT_INPUT_CSV = SCRIPT_DIR / "figures_9fluids_comparison" / "all_fluids_best_by_net_output.csv"
DEFAULT_OUTPUT_CSV = (
    SCRIPT_DIR
    / "figures_process_exergy_distribution_2year"
    / "process_exergy_distribution_vs_temperature_5year_step.csv"
)

FLUID_ORDER = [
    "R1234YF",
    "R1234ZEE",
    "R227EA",
    "R236EA",
    "R245FA",
    "R600A",
    "R600",
    "R601A",
    "R601",
]

REQUIRED_COLUMNS = [
    "fluid",
    "year",
    "T_HS_in_K",
    "net_output_kW",
    "eta_ex_percent",
    "Ed_total_W",
    "ratio_Ede_percent",
    "ratio_Edt_percent",
    "ratio_Edc_percent",
    "ratio_Edmix_percent",
    "ratio_Edp_percent",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export the process-wise exergy destruction ratio data used by the "
            "figures_process_exergy_distribution_2year plots."
        )
    )
    parser.add_argument(
        "--csv",
        type=str,
        default=str(DEFAULT_INPUT_CSV),
        help="Input all_fluids_best_by_net_output.csv path.",
    )
    parser.add_argument(
        "--out",
        type=str,
        default=str(DEFAULT_OUTPUT_CSV),
        help="Output CSV path.",
    )
    parser.add_argument(
        "--year-step",
        type=int,
        default=5,
        help="Sampling step in years. Use 5 to match the current figures_process_exergy_distribution_2year contents.",
    )
    return parser.parse_args()


def select_year_step_rows(df: pd.DataFrame, year_step: int) -> pd.DataFrame:
    year_values = df["year"].to_numpy(dtype=float)
    rounded_years = year_values.round().astype(int)
    mask_integer = (year_values - rounded_years).round(9) == 0
    mask_step = rounded_years % year_step == 0
    selected = df.loc[mask_integer & mask_step].copy()
    if selected.empty:
        raise ValueError(f"No rows matched the requested year step {year_step}.")
    return selected


def build_process_columns(df: pd.DataFrame) -> pd.DataFrame:
    eta_ex_fraction = df["eta_ex_percent"].to_numpy(dtype=float) / 100.0
    net_output_w = df["net_output_kW"].to_numpy(dtype=float) * 1000.0
    ein_w = net_output_w / eta_ex_fraction
    ed_total_w = df["Ed_total_W"].to_numpy(dtype=float)
    unused_w = ein_w - ed_total_w - net_output_w
    total_loss_w = ed_total_w + unused_w

    out = df.copy()
    out["T_HS_in_C"] = out["T_HS_in_K"].to_numpy(dtype=float) - 273.15
    out["ratio_unused_total_percent"] = unused_w / total_loss_w * 100.0
    out["ratio_Ede_total_percent"] = (
        out["ratio_Ede_percent"].to_numpy(dtype=float) * ed_total_w / total_loss_w
    )
    out["ratio_Edt_total_percent"] = (
        out["ratio_Edt_percent"].to_numpy(dtype=float) * ed_total_w / total_loss_w
    )
    out["ratio_Edc_total_percent"] = (
        (
            out["ratio_Edc_percent"].to_numpy(dtype=float)
            + out["ratio_Edmix_percent"].to_numpy(dtype=float)
        )
        * ed_total_w
        / total_loss_w
    )
    out["ratio_Edp_total_percent"] = (
        out["ratio_Edp_percent"].to_numpy(dtype=float) * ed_total_w / total_loss_w
    )
    out["ratio_sum_total_percent"] = (
        out["ratio_unused_total_percent"]
        + out["ratio_Ede_total_percent"]
        + out["ratio_Edt_total_percent"]
        + out["ratio_Edc_total_percent"]
        + out["ratio_Edp_total_percent"]
    )
    return out


def main() -> None:
    args = parse_args()
    csv_path = Path(args.csv).resolve()
    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(csv_path)
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise KeyError(f"Input CSV is missing required columns: {missing}")

    df = select_year_step_rows(df, args.year_step)
    df = build_process_columns(df)

    fluid_rank = {fluid: idx for idx, fluid in enumerate(FLUID_ORDER)}
    df["fluid_rank"] = df["fluid"].astype(str).str.upper().map(fluid_rank)
    df = df.sort_values(
        by=["fluid_rank", "T_HS_in_C", "year"],
        ascending=[True, True, True],
    ).reset_index(drop=True)

    export_df = df[
        [
            "fluid",
            "year",
            "T_HS_in_K",
            "T_HS_in_C",
            "ratio_unused_total_percent",
            "ratio_Ede_total_percent",
            "ratio_Edt_total_percent",
            "ratio_Edc_total_percent",
            "ratio_Edp_total_percent",
            "ratio_sum_total_percent",
        ]
    ].copy()

    export_df.to_csv(out_path, index=False, encoding="utf-8-sig")

    print(f"Input CSV: {csv_path}")
    print(f"Year step: {args.year_step}")
    print(f"Rows exported: {len(export_df)}")
    print(f"Output CSV: {out_path}")


if __name__ == "__main__":
    main()
