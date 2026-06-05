from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.font_manager import FontProperties
from matplotlib.ticker import MaxNLocator, MultipleLocator

SCRIPT_DIR = Path(__file__).resolve().parent

INPUT_DIRNAME = "figures_9fluids_comparison"
OUTPUT_DIRNAME = "figures_9fluids_comparison_refstyle"
AXES_WIDTH_HEIGHT_RATIO = 1.2
AXES_BOX_ASPECT = 1.0 / AXES_WIDTH_HEIGHT_RATIO
AXIS_LABEL_FONT_SIZE = 16
TABLE_FONT_SIZE = 7.4
TABLE_HEADER_FACE_COLOR = "#EFEFEF"
TABLE_EDGE_COLOR = "#B8B8B8"
TABLE_FIRST_COL_WIDTH = 0.14

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

FLUID_DISPLAY_NAMES = {
    "R1234YF": "R1234yf",
    "R1234ZEE": "R1234ze(E)",
    "R227EA": "R227ea",
    "R236EA": "R236ea",
    "R245FA": "R245fa",
    "R600A": "R600a",
    "R601A": "R601a",
}

FLUID_COLORS = {
    "R1234YF": "#FF00FF",
    "R1234ZEE": "#2E86FF",
    "R227EA": "#4C5A6B",
    "R236EA": "#E84A5F",
    "R245FA": "#C89B1B",
    "R600A": "#6F5AA8",
    "R600": "#7A7A7A",
    "R601A": "#D45500",
    "R601": "#2CA25F",
}

FLUID_MARKERS = {
    "R1234YF": "^",
    "R1234ZEE": "^",
    "R227EA": "s",
    "R236EA": "o",
    "R245FA": "<",
    "R600A": "D",
    "R600": "s",
    "R601A": ">",
    "R601": "v",
}


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
        "axes.linewidth": 1.2,
        "axes.labelsize": 12,
        "xtick.labelsize": 11,
        "ytick.labelsize": 11,
        "legend.fontsize": 8.4,
    }
)

SONGTI_FONT = FontProperties(family="SimSun")


def fluid_display_name(fluid: str) -> str:
    return FLUID_DISPLAY_NAMES.get(fluid, fluid)


def format_year_label(value: float) -> str:
    if np.isfinite(value) and np.isclose(value, round(value), atol=1e-9):
        return str(int(round(value)))
    return f"{value:g}"


def format_table_value(value: float) -> str:
    if pd.isna(value):
        return ""
    number = float(value)
    if not np.isfinite(number):
        return ""
    return f"{number:.2f}"


def add_metric_table(
    ax: plt.Axes,
    df: pd.DataFrame,
    y_columns: list[str],
) -> None:
    ax.axis("off")
    years = df["year"].to_numpy(dtype=float)
    col_labels = ["工质", *[format_year_label(year) for year in years]]
    cell_text = []

    for fluid in y_columns:
        row = [fluid_display_name(fluid)]
        row.extend(format_table_value(value) for value in df[fluid].to_numpy(dtype=float))
        cell_text.append(row)

    data_col_count = max(len(col_labels) - 1, 1)
    data_col_width = (1.0 - TABLE_FIRST_COL_WIDTH) / data_col_count
    table = ax.table(
        cellText=cell_text,
        colLabels=col_labels,
        cellLoc="center",
        loc="center",
        colWidths=[TABLE_FIRST_COL_WIDTH, *([data_col_width] * data_col_count)],
        bbox=[0.0, 0.02, 1.0, 0.96],
    )
    table.auto_set_font_size(False)

    for (row_index, col_index), cell in table.get_celld().items():
        cell.set_edgecolor(TABLE_EDGE_COLOR)
        cell.set_linewidth(0.6)
        cell.PAD = 0.02
        text = cell.get_text()
        text.set_fontsize(TABLE_FONT_SIZE)
        if row_index == 0:
            cell.set_facecolor(TABLE_HEADER_FACE_COLOR)
            text.set_weight("bold")
        if row_index == 0 and col_index == 0:
            text.set_fontproperties(SONGTI_FONT)
            text.set_fontsize(TABLE_FONT_SIZE)
        elif row_index > 0 and col_index == 0:
            fluid = y_columns[row_index - 1]
            text.set_color(FLUID_COLORS.get(fluid, "black"))
            text.set_weight("bold")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot 9-fluid comparison figures in a compact reference style."
    )
    parser.add_argument(
        "--indir",
        type=str,
        default=str(SCRIPT_DIR / INPUT_DIRNAME),
        help="Input directory containing the integer-year CSV files.",
    )
    parser.add_argument(
        "--outdir",
        type=str,
        default=str(SCRIPT_DIR / OUTPUT_DIRNAME),
        help="Output directory for the styled figures.",
    )
    parser.add_argument(
        "--year-step",
        type=int,
        default=5,
        help="Sampling step in years for plotting. Default is 5.",
    )
    return parser.parse_args()


def format_axis_label(chinese_text: str, unit: str | None = None) -> str:
    if unit is None:
        return chinese_text

    unit_math = unit.replace("%", r"\%")
    return chinese_text + rf" $\mathrm{{({unit_math})}}$"


def style_axes(ax: plt.Axes, x: pd.Series, ylabel: str) -> None:
    ax.set_xlabel("年份", fontproperties=SONGTI_FONT)
    ax.set_ylabel(ylabel, fontproperties=SONGTI_FONT)
    ax.xaxis.label.set_fontsize(AXIS_LABEL_FONT_SIZE)
    ax.yaxis.label.set_fontsize(AXIS_LABEL_FONT_SIZE)
    ax.set_xlim(float(x.min()) - 0.8, float(x.max()) + 0.8)
    ax.set_box_aspect(AXES_BOX_ASPECT)
    ax.xaxis.set_major_locator(MultipleLocator(5.0))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=6))
    ax.tick_params(axis="both", which="major", direction="in", length=4, width=1.0)
    for spine in ax.spines.values():
        spine.set_linewidth(1.2)


def set_padded_ylim(
    ax: plt.Axes,
    series_list: list[np.ndarray],
    bottom_pad_ratio: float = 0.04,
    top_pad_ratio: float = 0.18,
) -> None:
    data = np.concatenate([arr[np.isfinite(arr)] for arr in series_list if np.isfinite(arr).any()])
    y_min = float(data.min())
    y_max = float(data.max())
    span = y_max - y_min
    if span <= 0:
        span = max(abs(y_max), 1.0) * 0.05
    bottom_pad = span * bottom_pad_ratio
    top_pad = span * top_pad_ratio
    ax.set_ylim(y_min - bottom_pad, y_max + top_pad)


def plot_metric(
    df: pd.DataFrame,
    y_columns: list[str],
    ylabel: str,
    outpath: Path,
    legend_ncol: int = 2,
) -> None:
    fig = plt.figure(figsize=(10.8, 11.2))
    grid = fig.add_gridspec(
        nrows=2,
        ncols=1,
        height_ratios=[4.0, 1.25],
        hspace=0.18,
    )
    ax = fig.add_subplot(grid[0])
    table_ax = fig.add_subplot(grid[1])
    x = df["year"]
    plotted_values: list[np.ndarray] = []

    for fluid in y_columns:
        y = df[fluid].to_numpy(dtype=float)
        plotted_values.append(y)
        ax.plot(
            x,
            y,
            color=FLUID_COLORS[fluid],
            marker=FLUID_MARKERS[fluid],
            linewidth=1.8,
            markersize=6.6,
            markerfacecolor=FLUID_COLORS[fluid],
            markeredgecolor=FLUID_COLORS[fluid],
            markeredgewidth=0.9,
            label=fluid_display_name(fluid),
        )

    style_axes(ax, x, ylabel)
    set_padded_ylim(ax, plotted_values, bottom_pad_ratio=0.04, top_pad_ratio=0.18)
    ax.legend(
        loc="upper right",
        bbox_to_anchor=(0.985, 0.985),
        ncol=legend_ncol,
        frameon=True,
        fancybox=False,
        framealpha=1.0,
        facecolor="white",
        edgecolor="#B8B8B8",
        borderpad=0.28,
        columnspacing=0.85,
        handlelength=2.0,
        handletextpad=0.45,
        labelspacing=0.35,
        borderaxespad=0.2,
    )
    add_metric_table(table_ax, df, y_columns)
    fig.subplots_adjust(left=0.08, right=0.985, top=0.97, bottom=0.045, hspace=0.18)
    fig.savefig(outpath, bbox_inches="tight")
    plt.close(fig)


def ordered_columns(df: pd.DataFrame) -> list[str]:
    return [fluid for fluid in FLUID_ORDER if fluid in df.columns]


def select_year_step_rows(df: pd.DataFrame, year_step: int) -> pd.DataFrame:
    year_values = df["year"].to_numpy(dtype=float)
    rounded_years = np.round(year_values).astype(int)
    mask_integer = np.isclose(year_values, rounded_years, atol=1e-9)
    mask_step = np.mod(rounded_years, year_step) == 0
    selected = df.loc[mask_integer & mask_step].copy()
    if selected.empty:
        raise ValueError(f"No rows matched the requested year step {year_step}.")
    return selected


def main() -> None:
    args = parse_args()
    indir = Path(args.indir).resolve()
    outdir = Path(args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    net_output = pd.read_csv(indir / "02_net_output_integer_year_points.csv")
    exergy_eff = pd.read_csv(indir / "03_exergy_efficiency_integer_year_points.csv")
    exergy_dest = pd.read_csv(indir / "04_exergy_destruction_integer_year_points.csv")
    lmtd = pd.read_csv(indir / "06_07_lmtd_integer_year_points.csv")
    lmtd_cond = pd.read_csv(indir / "08_lmtd_condenser_integer_year_points.csv")

    net_output = select_year_step_rows(net_output, args.year_step)
    exergy_eff = select_year_step_rows(exergy_eff, args.year_step)
    exergy_dest = select_year_step_rows(exergy_dest, args.year_step)
    lmtd = select_year_step_rows(lmtd, args.year_step)
    lmtd_cond = select_year_step_rows(lmtd_cond, args.year_step)

    plot_metric(
        net_output,
        ordered_columns(net_output),
        format_axis_label("净输出功", "kW"),
        outdir / "02_net_output_ref_style.png",
    )
    plot_metric(
        exergy_eff,
        ordered_columns(exergy_eff),
        format_axis_label("㶲效率", "%"),
        outdir / "03_exergy_efficiency_ref_style.png",
    )
    plot_metric(
        exergy_dest,
        ordered_columns(exergy_dest),
        format_axis_label("㶲损", "kW"),
        outdir / "04_exergy_destruction_ref_style.png",
    )

    hp_columns = [fluid for fluid in FLUID_ORDER if f"{fluid}_HP_K" in lmtd.columns]
    lp_columns = [fluid for fluid in FLUID_ORDER if f"{fluid}_LP_K" in lmtd.columns]

    hp_df = pd.DataFrame({"year": lmtd["year"]})
    for fluid in hp_columns:
        hp_df[fluid] = lmtd[f"{fluid}_HP_K"]
    plot_metric(
        hp_df,
        hp_columns,
        format_axis_label("高压侧对数平均温差", "K"),
        outdir / "06_lmtd_hp_ref_style.png",
    )

    lp_df = pd.DataFrame({"year": lmtd["year"]})
    for fluid in lp_columns:
        lp_df[fluid] = lmtd[f"{fluid}_LP_K"]
    plot_metric(
        lp_df,
        lp_columns,
        format_axis_label("低压侧对数平均温差", "K"),
        outdir / "07_lmtd_lp_ref_style.png",
    )

    plot_metric(
        lmtd_cond,
        ordered_columns(lmtd_cond),
        format_axis_label("\u51b7\u51dd\u5668\u5bf9\u6570\u5e73\u5747\u6e29\u5dee", "K"),
        outdir / "08_lmtd_condenser_ref_style.png",
    )

    print(f"Input directory: {indir}")
    print(f"Year step: {args.year_step}")
    print(f"Output directory: {outdir}")


if __name__ == "__main__":
    main()
