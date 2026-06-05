from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import MultipleLocator

SCRIPT_DIR = Path(__file__).resolve().parent

DEFAULT_INPUT_CSV = SCRIPT_DIR / "figures_9fluids_comparison" / "all_fluids_best_by_net_output.csv"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "figures_process_exergy_distribution"

PROCESS_SPECS = [
    {
        "column": "ratio_unused_total_percent",
        "label": "热源未利用",
        "color": "#495057",
        "text_color": "white",
        "xfrac": 0.16,
        "label_mode": "inside",
    },
    {
        "column": "ratio_Ede_total_percent",
        "label": "吸热过程换热温差",
        "color": "#F2B447",
        "text_color": "#1F1F1F",
        "xfrac": 0.28,
        "label_mode": "inside",
    },
    {
        "column": "ratio_Edt_total_percent",
        "label": "膨胀过程",
        "color": "#4C78A8",
        "text_color": "white",
        "xfrac": 0.26,
        "label_mode": "inside",
    },
    {
        "column": "ratio_Edc_total_percent",
        "label": "冷凝过程",
        "color": "#72B7B2",
        "text_color": "#1F1F1F",
        "xfrac": 0.20,
        "label_mode": "inside",
    },
    {
        "column": "ratio_Edp_total_percent",
        "label": "压缩过程",
        "color": "#E45756",
        "text_color": "white",
        "xfrac": 0.92,
        "label_mode": "arrow",
        "text_axes": (0.86, 0.90),
    },
]


plt.rcParams.update(
    {
        "font.family": ["Times New Roman", "SimSun"],
        "font.serif": ["Times New Roman"],
        "font.sans-serif": ["SimSun"],
        "mathtext.fontset": "custom",
        "mathtext.rm": "Times New Roman",
        "mathtext.it": "Times New Roman:italic",
        "mathtext.bf": "Times New Roman:bold",
        "axes.unicode_minus": False,
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "axes.labelsize": 13,
        "xtick.labelsize": 11,
        "ytick.labelsize": 11,
    }
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot process-wise exergy destruction distribution from figures_9fluids_comparison CSV data."
    )
    parser.add_argument(
        "--csv",
        type=str,
        default=str(DEFAULT_INPUT_CSV),
        help="Input all_fluids_best_by_net_output.csv path.",
    )
    parser.add_argument(
        "--outdir",
        type=str,
        default=str(DEFAULT_OUTPUT_DIR),
        help="Output directory for process exergy distribution figures.",
    )
    parser.add_argument(
        "--fluid",
        type=str,
        default=None,
        help="Optional fluid name filter, e.g. R600A. If omitted, plot all fluids in the CSV.",
    )
    return parser.parse_args()


def style_axes(ax: plt.Axes, x_c: np.ndarray) -> None:
    ax.set_xlabel("热源入口温度（℃）")
    ax.set_ylabel("㶲损占比（%）")
    ax.set_xlim(float(x_c.min()), float(x_c.max()))
    ax.set_ylim(0, 100)
    ax.margins(x=0)
    ax.xaxis.set_major_locator(MultipleLocator(5.0))
    ax.yaxis.set_major_locator(MultipleLocator(20.0))
    ax.tick_params(axis="both", which="major", direction="in", length=4, width=1.0)
    for spine in ax.spines.values():
        spine.set_linewidth(1.2)


def place_inside_label(
    ax: plt.Axes,
    x: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    text: str,
    xfrac: float,
    text_color: str,
) -> None:
    idx = int(round((len(x) - 1) * xfrac))
    ymid = 0.5 * (lower[idx] + upper[idx])
    ax.text(
        x[idx],
        ymid,
        text,
        color=text_color,
        fontsize=13,
        ha="center",
        va="center",
    )


def place_arrow_label(
    ax: plt.Axes,
    x: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    text: str,
    xfrac: float,
    text_axes: tuple[float, float],
    text_color: str,
) -> None:
    idx = int(round((len(x) - 1) * xfrac))
    ymid = 0.5 * (lower[idx] + upper[idx])
    ax.annotate(
        text,
        xy=(x[idx], ymid),
        xycoords="data",
        xytext=text_axes,
        textcoords="axes fraction",
        ha="center",
        va="center",
        color=text_color,
        fontsize=13,
        arrowprops={"arrowstyle": "->", "color": text_color, "lw": 1.0},
    )


def plot_single_fluid(fluid_df: pd.DataFrame, outdir: Path) -> Path:
    fluid = str(fluid_df["fluid"].iloc[0])
    plot_df = fluid_df.sort_values("T_HS_in_K").reset_index(drop=True).copy()
    plot_df["T_HS_in_C"] = plot_df["T_HS_in_K"] - 273.15

    ein_w = plot_df["net_output_kW"].to_numpy(dtype=float) * 1000.0 / (
        plot_df["eta_ex_percent"].to_numpy(dtype=float) / 100.0
    )
    ed_total_w = plot_df["Ed_total_W"].to_numpy(dtype=float)
    net_output_w = plot_df["net_output_kW"].to_numpy(dtype=float) * 1000.0
    unused_w = ein_w - ed_total_w - net_output_w
    total_loss_w = ed_total_w + unused_w

    plot_df["ratio_unused_total_percent"] = unused_w / total_loss_w * 100.0
    plot_df["ratio_Ede_total_percent"] = plot_df["ratio_Ede_percent"].to_numpy(dtype=float) * ed_total_w / total_loss_w
    plot_df["ratio_Edt_total_percent"] = plot_df["ratio_Edt_percent"].to_numpy(dtype=float) * ed_total_w / total_loss_w
    plot_df["ratio_Edc_total_percent"] = (
        (plot_df["ratio_Edc_percent"].to_numpy(dtype=float) + plot_df["ratio_Edmix_percent"].to_numpy(dtype=float))
        * ed_total_w
        / total_loss_w
    )
    plot_df["ratio_Edp_total_percent"] = plot_df["ratio_Edp_percent"].to_numpy(dtype=float) * ed_total_w / total_loss_w

    x = plot_df["T_HS_in_C"].to_numpy(dtype=float)
    layers = [plot_df[spec["column"]].to_numpy(dtype=float) for spec in PROCESS_SPECS]

    fig, ax = plt.subplots(figsize=(8.4, 6.6))
    ax.stackplot(
        x,
        layers,
        colors=[spec["color"] for spec in PROCESS_SPECS],
        alpha=1.0,
        linewidth=0.0,
    )
    style_axes(ax, x)

    cumulative = np.cumsum(np.vstack(layers), axis=0)
    lowers = np.vstack([np.zeros_like(x), cumulative[:-1]])
    uppers = cumulative
    for idx, spec in enumerate(PROCESS_SPECS):
        lower = lowers[idx]
        upper = uppers[idx]
        if spec["label_mode"] == "inside":
            place_inside_label(ax, x, lower, upper, spec["label"], spec["xfrac"], spec["text_color"])
        else:
            place_arrow_label(
                ax,
                x,
                lower,
                upper,
                spec["label"],
                spec["xfrac"],
                spec["text_axes"],
                spec["text_color"],
            )

    ax.text(
        0.5,
        0.94,
        fluid,
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=16,
        color="#1F1F1F",
        fontweight="bold",
    )

    fig.subplots_adjust(left=0.13, right=0.98, top=0.97, bottom=0.14)
    outpath = outdir / f"{fluid}_process_exergy_distribution.png"
    fig.savefig(outpath, bbox_inches="tight")
    plt.close(fig)
    return outpath


def main() -> None:
    args = parse_args()
    csv_path = Path(args.csv).resolve()
    outdir = Path(args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(csv_path)
    required_cols = [
        "fluid",
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
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise KeyError(f"Input CSV is missing required columns: {missing}")

    if args.fluid:
        df = df[df["fluid"].astype(str).str.upper() == args.fluid.upper()].copy()
        if df.empty:
            raise ValueError(f"No rows found for fluid {args.fluid} in {csv_path}")

    outputs = []
    for fluid, fluid_df in df.groupby("fluid", sort=False):
        outputs.append(plot_single_fluid(fluid_df, outdir))

    print(f"Input CSV: {csv_path}")
    print(f"Output directory: {outdir}")
    for outpath in outputs:
        print(f"Generated: {outpath}")


if __name__ == "__main__":
    main()
