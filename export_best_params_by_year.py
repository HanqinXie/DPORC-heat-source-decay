from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT_CSV = SCRIPT_DIR / "R1234yf_40year_twostage_all_feasible_2026-04-18_20-16-01.csv"


def default_output_path(input_csv: Path) -> Path:
    return input_csv.with_name(f"{input_csv.stem}_best_params_by_year.csv")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the best-by-year parameter rows using the maximum net_output_kW in each year."
    )
    parser.add_argument(
        "--csv",
        type=str,
        default=str(DEFAULT_INPUT_CSV),
        help="Input feasible-results CSV path.",
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="Output CSV path. Defaults to <input_stem>_best_params_by_year.csv.",
    )
    parser.add_argument(
        "--chunksize",
        type=int,
        default=200_000,
        help="Chunk size used when streaming the large CSV file.",
    )
    return parser.parse_args()


def update_best_rows(
    best_by_year: dict[float, pd.Series],
    candidate_rows: pd.DataFrame,
) -> None:
    for _, row in candidate_rows.iterrows():
        year = float(row["year"])
        net_output = float(row["net_output_kW"])
        current = best_by_year.get(year)
        if current is None or net_output > float(current["net_output_kW"]):
            best_by_year[year] = row.copy()


def export_best_rows(input_csv: Path, output_csv: Path, chunksize: int) -> pd.DataFrame:
    best_by_year: dict[float, pd.Series] = {}
    processed_rows = 0
    chunk_count = 0

    for chunk in pd.read_csv(input_csv, chunksize=chunksize):
        chunk_count += 1
        processed_rows += len(chunk)

        required_cols = {"year", "net_output_kW"}
        missing = required_cols.difference(chunk.columns)
        if missing:
            raise KeyError(f"Input CSV is missing required columns: {sorted(missing)}")

        best_idx = chunk.groupby("year")["net_output_kW"].idxmax()
        candidate_rows = chunk.loc[best_idx].copy()
        update_best_rows(best_by_year, candidate_rows)

    if not best_by_year:
        raise ValueError(f"No valid rows were found in {input_csv}")

    best_df = (
        pd.DataFrame(best_by_year.values())
        .sort_values("year")
        .reset_index(drop=True)
    )
    best_df.to_csv(output_csv, index=False, encoding="utf-8-sig")

    print(f"Input CSV: {input_csv}")
    print(f"Processed chunks: {chunk_count}")
    print(f"Processed rows: {processed_rows}")
    print(f"Years exported: {len(best_df)}")
    print(f"Output CSV: {output_csv}")
    print("Selection rule: choose the row with the maximum net_output_kW in each year.")
    return best_df


def main() -> None:
    args = parse_args()
    input_csv = Path(args.csv).resolve()
    output_csv = Path(args.out).resolve() if args.out else default_output_path(input_csv)
    export_best_rows(input_csv, output_csv, args.chunksize)


if __name__ == "__main__":
    main()
