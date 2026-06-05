from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import MaxNLocator, MultipleLocator, NullLocator
from scipy.interpolate import PchipInterpolator

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent

# The script searches the chosen directory for the latest CSV of each target fluid.
TARGET_FLUIDS = [
    "R1234yf",
    "R1234ZEE",
    "R227EA",
    "R236ea",
    "R245FA",
    "isobutane",
    "Butane",
    "Isopentane",
    "Pentane",
]

DEFAULT_OUTPUT_NAME = "9fluids_comparison"

FLUID_COLORS = {
    "R1234yf": "#005F73",
    "R1234ZEE": "#0A9396",
    "R227EA": "#94D2BD",
    "R236ea": "#EE9B00",
    "R245FA": "#CA6702",
    "isobutane": "#BB3E03",
    "Butane": "#AE2012",
    "Isopentane": "#6A4C93",
    "Pentane": "#3A86FF",
}

FLUID_DISPLAY_NAMES = {
    "R1234yf": "R1234YF",
    "R1234ZEE": "R1234ZEE",
    "R227EA": "R227EA",
    "R236ea": "R236EA",
    "R245FA": "R245FA",
    "isobutane": "R600A",
    "Butane": "R600",
    "Isopentane": "R601A",
    "Pentane": "R601",
}

STATE_POINT_YEARS = np.array([0, 5, 10, 15, 20, 25, 30, 35, 40], dtype=float)
AXES_FRAME_WIDTH_HEIGHT_RATIO = 1.2
AXES_BOX_ASPECT = 1.0 / AXES_FRAME_WIDTH_HEIGHT_RATIO

WIDE_FIGSIZE = (8.8, 8.8)
WIDE_FIGSIZE_LMTD = (8.8, 8.8)
LEGEND_NCOL = 3
LMTD_COMPARE_FLUIDS = ["R1234yf", "isobutane"]
LMTD_COMPARE_YEARS = [0, 30]
LMTD_COMPARE_COMPONENTS = [
    ("高压蒸发器", "lmtd_hp_K"),
    ("低压蒸发器", "lmtd_lp_K"),
]



# 统一绘图风格，兼顾中文显示与论文排版观感
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
        "axes.spines.top": True,
        "axes.spines.right": True,
        "axes.grid": False,
        "axes.facecolor": "#FCFCFC",
        "figure.facecolor": "white",
        "axes.labelsize": 11,
        "axes.titlesize": 13,
        "legend.fontsize": 9,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
    }
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate paper-style comparison plots from selected ORC working-fluid CSV results."
    )
    parser.add_argument(
        "--csv",
        type=str,
        default=None,
        help="Optional CSV directory or a sample CSV path. The script searches that directory for the selected working-fluid CSV files.",
    )
    parser.add_argument(
        "--outdir",
        type=str,
        default=None,
        help="Output directory. If omitted, create figures_9fluids_comparison automatically.",
    )
    return parser.parse_args()


def resolve_search_dir(csv_arg: str | None) -> Path:
    search_roots = [Path.cwd(), SCRIPT_DIR, PROJECT_DIR]
    if not csv_arg:
        return SCRIPT_DIR

    raw_path = Path(csv_arg).expanduser()
    candidate_paths = []
    if raw_path.is_absolute():
        candidate_paths.append(raw_path)
    else:
        candidate_paths.extend((root / raw_path).resolve() for root in search_roots)

    for candidate in candidate_paths:
        if candidate.exists():
            return candidate.resolve() if candidate.is_dir() else candidate.resolve().parent

    raise FileNotFoundError(
        f"CSV directory or sample CSV not found: {csv_arg}. Checked: "
        + ", ".join(str(path) for path in candidate_paths)
    )


def find_latest_csv_for_fluid(search_dir: Path, fluid: str) -> Path:
    files = sorted(
        {path.resolve() for path in search_dir.glob(f"{fluid}_40year_twostage_all_feasible_*.csv")},
        key=lambda path: path.stat().st_mtime,
    )
    if not files:
        raise FileNotFoundError(
            f"No matching CSV found for {fluid} in {search_dir}. "
            f"Expected pattern: {fluid}_40year_twostage_all_feasible_*.csv"
        )
    return files[-1]


def resolve_fluid_csv_paths(search_dir: Path) -> dict[str, Path]:
    return {fluid: find_latest_csv_for_fluid(search_dir, fluid) for fluid in TARGET_FLUIDS}


def get_fluid_display_name(fluid: str) -> str:
    return FLUID_DISPLAY_NAMES.get(fluid, fluid.upper())


def load_and_filter(csv_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.read_csv(csv_path)
    required_cols = [
        "year",
        "T_HS_in_K",
        "net_output_kW",
        "eta_ex_percent",
        "Ed_total_W",
        "ratio_Ede_percent",
        "ratio_Edt_percent",
        "ratio_Edp_percent",
        "ratio_Edmix_percent",
        "ratio_Edc_percent",
        "lmtd_hp_K",
        "lmtd_lp_K",
    ]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise KeyError(f"CSV is missing required columns: {missing}")

    best_idx = df.groupby("year")["net_output_kW"].idxmax()
    best = df.loc[best_idx].sort_values("year").reset_index(drop=True)
    return df, best


def save_best_csv(best_by_fluid: dict[str, pd.DataFrame], outdir: Path) -> Path:
    rows = []
    for fluid in TARGET_FLUIDS:
        fluid_best = best_by_fluid[fluid].copy()
        fluid_best.insert(0, "fluid", get_fluid_display_name(fluid))
        rows.append(fluid_best)
    out_csv = outdir / "all_fluids_best_by_net_output.csv"
    pd.concat(rows, ignore_index=True).to_csv(out_csv, index=False, encoding="utf-8-sig")
    return out_csv


def get_integer_year_points(best: pd.DataFrame) -> pd.DataFrame:
    integer_mask = np.isclose(best["year"], np.round(best["year"]), atol=1e-9)
    return best.loc[integer_mask].copy().reset_index(drop=True)


def get_integer_year_mask(best: pd.DataFrame) -> np.ndarray:
    return np.isclose(best["year"], np.round(best["year"]), atol=1e-9)


def get_all_years(best_by_fluid: dict[str, pd.DataFrame]) -> pd.Series:
    return pd.concat([best_by_fluid[fluid]["year"] for fluid in TARGET_FLUIDS], ignore_index=True)


def round_numeric_columns(df: pd.DataFrame, decimals: int = 2) -> pd.DataFrame:
    out = df.copy()
    numeric_cols = out.select_dtypes(include=[np.number]).columns
    out[numeric_cols] = out[numeric_cols].round(decimals)
    return out


def export_plot_point_csv(
    outdir: Path,
    figure_prefix: str,
    figure_slug: str,
    data: pd.DataFrame,
) -> Path:
    out_csv = outdir / f"{figure_prefix}_{figure_slug}_integer_year_points.csv"
    round_numeric_columns(data).to_csv(out_csv, index=False, encoding="utf-8-sig")
    return out_csv


def infer_monotonic_direction(y) -> str:
    y = np.asarray(y, dtype=float)
    finite = y[np.isfinite(y)]
    if finite.size <= 1:
        return "decreasing"
    if finite[-1] > finite[0]:
        return "increasing"
    if finite[-1] < finite[0]:
        return "decreasing"
    diffs = np.diff(finite)
    if np.nansum(diffs) >= 0:
        return "increasing"
    return "decreasing"


def isotonic_regression(y, increasing: bool = True):
    y = np.asarray(y, dtype=float)
    if y.size <= 1:
        return y.copy()
    if not increasing:
        return -isotonic_regression(-y, increasing=True)

    blocks = []
    for idx, value in enumerate(y):
        blocks.append([float(value), 1.0, idx, idx])
        while len(blocks) >= 2 and blocks[-2][0] > blocks[-1][0]:
            v1, w1, s1, _ = blocks[-2]
            v2, w2, _, e2 = blocks[-1]
            new_weight = w1 + w2
            new_value = (v1 * w1 + v2 * w2) / new_weight
            blocks[-2:] = [[new_value, new_weight, s1, e2]]

    out = np.empty_like(y, dtype=float)
    for value, _, start, end in blocks:
        out[start : end + 1] = value
    return out


def enforce_monotonic(y, direction: str = "auto"):
    y = np.asarray(y, dtype=float)
    resolved = infer_monotonic_direction(y) if direction == "auto" else direction
    if resolved not in {"increasing", "decreasing"}:
        raise ValueError(f"Unsupported monotonic direction: {resolved}")
    y_mono = isotonic_regression(y, increasing=(resolved == "increasing"))
    return y_mono, resolved


def smooth_xy(x, y, points: int = 400, direction: str = "auto"):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    y_mono, resolved = enforce_monotonic(y, direction=direction)
    x_dense = np.linspace(x.min(), x.max(), points)
    y_dense = PchipInterpolator(x, y_mono)(x_dense)
    if resolved == "increasing":
        y_dense = np.maximum.accumulate(y_dense)
    else:
        y_dense = np.minimum.accumulate(y_dense)
    return y_mono, x_dense, y_dense, resolved


def smooth_display_series(y, window: int = 5, direction: str = "auto"):
    """Light display-only smoothing: median then mean rolling filters."""
    s = pd.Series(np.asarray(y, dtype=float))
    s = s.rolling(window=window, center=True, min_periods=1).median()
    s = s.rolling(window=window, center=True, min_periods=1).mean()
    y_mono, _ = enforce_monotonic(s.to_numpy(dtype=float), direction=direction)
    return y_mono


def normalize_composition_rows(y_matrix: np.ndarray, total: float = 100.0) -> np.ndarray:
    y_matrix = np.asarray(y_matrix, dtype=float)
    sums = y_matrix.sum(axis=0)
    return np.divide(y_matrix, sums, out=np.zeros_like(y_matrix), where=sums > 0) * total


def build_monotonic_composition(
    x,
    series,
    raw_values: dict[str, np.ndarray],
    points: int = 400,
) -> tuple[np.ndarray, dict[str, np.ndarray], np.ndarray]:
    x = np.asarray(x, dtype=float)
    x_dense = np.linspace(x.min(), x.max(), points)
    raw_matrix = np.vstack([
        np.clip(np.asarray(raw_values[col], dtype=float), 0, None)
        for col, _, _ in series
    ])
    raw_boundaries = np.cumsum(raw_matrix, axis=0)

    boundary_directions = []
    yearly_boundaries = []
    for idx in range(len(series) - 1):
        direction = infer_monotonic_direction(raw_boundaries[idx])
        boundary_directions.append(direction)
        yearly_boundaries.append(enforce_monotonic(raw_boundaries[idx], direction=direction)[0])

    yearly_boundaries = np.vstack(yearly_boundaries + [np.full_like(x, 100.0)])
    yearly_boundaries = np.maximum.accumulate(np.clip(yearly_boundaries, 0, 100), axis=0)
    yearly_boundaries[-1] = 100.0
    yearly_matrix = np.vstack([yearly_boundaries[0], np.diff(yearly_boundaries, axis=0)])

    dense_boundaries = []
    for idx in range(len(series) - 1):
        boundary_dense = PchipInterpolator(x, yearly_boundaries[idx])(x_dense)
        if boundary_directions[idx] == "increasing":
            boundary_dense = np.maximum.accumulate(boundary_dense)
        else:
            boundary_dense = np.minimum.accumulate(boundary_dense)
        dense_boundaries.append(np.clip(boundary_dense, 0, 100))

    dense_boundaries = np.vstack(dense_boundaries + [np.full_like(x_dense, 100.0)])
    dense_boundaries = np.maximum.accumulate(np.clip(dense_boundaries, 0, 100), axis=0)
    dense_boundaries[-1] = 100.0
    dense_matrix = np.vstack([dense_boundaries[0], np.diff(dense_boundaries, axis=0)])

    monotonic_yearly = {col: yearly_matrix[idx] for idx, (col, _, _) in enumerate(series)}
    return x_dense, monotonic_yearly, dense_matrix


def get_state_point_mask(x, years: np.ndarray | None = None) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    years = STATE_POINT_YEARS if years is None else np.asarray(years, dtype=float)
    return np.any(np.isclose(x[:, None], years[None, :], atol=1e-9), axis=1)


def plot_raw_and_smooth(
    ax: plt.Axes,
    x,
    y,
    color: str,
    label: str,
    marker: str = "^",
    linewidth: float = 2.3,
    markersize: float = 6.8,
) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    y_mono, x_dense, y_dense, _ = smooth_xy(x, y)
    ax.plot(x_dense, y_dense, color=color, linewidth=linewidth, label=label)
    state_point_mask = get_state_point_mask(x)
    ax.plot(
        x[state_point_mask],
        y_mono[state_point_mask],
        linestyle="none",
        marker=marker,
        markersize=markersize,
        markerfacecolor=color,
        markeredgecolor=color,
        markeredgewidth=1.2,
        color=color,
    )
    return y_mono


def plot_step_series(
    ax: plt.Axes,
    x,
    y,
    color: str,
    label: str,
    marker: str = "^",
    linewidth: float = 2.0,
    markersize: float = 6.2,
) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    ax.step(x, y, where="post", color=color, linewidth=linewidth, label=label, zorder=2.0)
    state_point_mask = get_state_point_mask(x)
    ax.plot(
        x[state_point_mask],
        y[state_point_mask],
        linestyle="none",
        marker=marker,
        markersize=markersize,
        markerfacecolor=color,
        markeredgecolor=color,
        markeredgewidth=1.2,
        color=color,
        zorder=3.0,
    )
    return y


def style_axes(
    ax: plt.Axes,
    xlabel: str = "\u5e74\u4efd",
    ylabel: str = "",
    xdata: pd.Series | None = None,
    zero_bottom: bool = False,
) -> None:
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if xdata is not None:
        ax.set_xlim(xdata.min(), xdata.max())
    elif ax.get_lines():
        ax.set_xlim(ax.get_lines()[0].get_xdata().min(), ax.get_lines()[0].get_xdata().max())
    ax.margins(x=0)
    if zero_bottom:
        ax.set_ylim(bottom=0)
    ax.set_box_aspect(AXES_BOX_ASPECT)
    ax.xaxis.set_major_locator(MultipleLocator(5.0))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.yaxis.set_minor_locator(NullLocator())
    ax.tick_params(axis="x", which="major", top=False, direction="in")
    ax.tick_params(axis="y", which="major", right=False, direction="in")
    for spine in ax.spines.values():
        spine.set_linewidth(1.2)
    ax.spines["top"].set_visible(True)
    ax.spines["right"].set_visible(True)


def save_figure(fig: plt.Figure, outpath: Path) -> None:
    fig.tight_layout()
    fig.savefig(outpath, bbox_inches="tight")
    plt.close(fig)


def reorder_legend_for_row_major(handles, labels, ncol: int):
    total = len(labels)
    nrow = int(np.ceil(total / ncol))
    order = []
    for c in range(ncol):
        for r in range(nrow):
            idx = r * ncol + c
            if idx < total:
                order.append(idx)
    return [handles[i] for i in order], [labels[i] for i in order]


def reorder_legend_by_label(handles, labels, desired_order):
    label_to_handle = {label: handle for handle, label in zip(handles, labels)}
    ordered_labels = [label for label in desired_order if label in label_to_handle]
    ordered_handles = [label_to_handle[label] for label in ordered_labels]
    return ordered_handles, ordered_labels


def set_data_filled_ylim(ax: plt.Axes, series_list, pad_ratio: float = 0.08) -> None:
    finite_chunks = []
    for values in series_list:
        arr = np.asarray(values, dtype=float)
        finite = arr[np.isfinite(arr)]
        if finite.size:
            finite_chunks.append(finite)
    if not finite_chunks:
        return

    data = np.concatenate(finite_chunks)
    y_min = float(data.min())
    y_max = float(data.max())
    span = y_max - y_min
    scale = max(abs(y_min), abs(y_max), 1.0)
    pad = max(span * pad_ratio, scale * 0.02)

    if span < scale * 0.05:
        pad = max(pad, scale * 0.04)

    lower = y_min - pad
    upper = y_max + pad
    if y_min >= 0:
        lower = max(0.0, lower)
    ax.set_ylim(lower, upper)


def find_year_index(best: pd.DataFrame, year_value: float) -> int:
    year_array = best["year"].to_numpy(dtype=float)
    matches = np.flatnonzero(np.isclose(year_array, year_value, atol=1e-9))
    if matches.size == 0:
        raise KeyError(f"Year {year_value} not found in the best-by-year data.")
    return int(matches[0])


def plot_multi_fluid_metric(
    best_by_fluid: dict[str, pd.DataFrame],
    outdir: Path,
    figure_prefix: str,
    figure_slug: str,
    outname: str,
    ylabel: str,
    value_getter,
    figsize: tuple[float, float] = WIDE_FIGSIZE,
) -> None:
    fig, ax = plt.subplots(figsize=figsize)
    points = None
    all_years = get_all_years(best_by_fluid)
    plotted_values = []

    for fluid in TARGET_FLUIDS:
        best = best_by_fluid[fluid]
        integer_mask = get_integer_year_mask(best)
        label = get_fluid_display_name(fluid)
        y_plot = plot_raw_and_smooth(
            ax,
            best["year"],
            value_getter(best),
            FLUID_COLORS[fluid],
            label,
            linewidth=2.0,
            markersize=6.4,
        )
        plotted_values.append(y_plot)
        if points is None:
            points = pd.DataFrame({"year": best.loc[integer_mask, "year"].reset_index(drop=True)})
        points[label] = y_plot[integer_mask]

    style_axes(ax, ylabel=ylabel, xdata=all_years, zero_bottom=False)
    set_data_filled_ylim(ax, plotted_values, pad_ratio=0.08)

    handles, labels = ax.get_legend_handles_labels()
    desired_order = [get_fluid_display_name(fluid) for fluid in TARGET_FLUIDS]
    handles, labels = reorder_legend_by_label(handles, labels, desired_order)
    handles, labels = reorder_legend_for_row_major(handles, labels, LEGEND_NCOL)
    ax.legend(
        handles,
        labels,
        frameon=False,
        ncol=LEGEND_NCOL,
        loc="upper right",
        bbox_to_anchor=(0.985, 0.985),
        columnspacing=0.9,
        handletextpad=0.7,
        fontsize=7.2,
        borderaxespad=0.2,
        labelspacing=0.35,
    )
    fig.subplots_adjust(left=0.12, right=0.985, top=0.98, bottom=0.10)
    fig.savefig(outdir / outname, bbox_inches="tight")
    plt.close(fig)
    export_plot_point_csv(outdir, figure_prefix, figure_slug, points)


def plot_net_power(best_by_fluid: dict[str, pd.DataFrame], outdir: Path) -> None:
    plot_multi_fluid_metric(
        best_by_fluid,
        outdir,
        "02",
        "net_output",
        "02_net_output_vs_year.png",
        "\u51c0\u8f93\u51fa\u529f (kW)",
        lambda best: best["net_output_kW"],
    )


def plot_exergy_efficiency(best_by_fluid: dict[str, pd.DataFrame], outdir: Path) -> None:
    plot_multi_fluid_metric(
        best_by_fluid,
        outdir,
        "03",
        "exergy_efficiency",
        "03_exergy_efficiency_vs_year.png",
        "\u3db2\u6548\u7387 (%)",
        lambda best: best["eta_ex_percent"],
    )


def plot_exergy_destruction(best_by_fluid: dict[str, pd.DataFrame], outdir: Path) -> None:
    plot_multi_fluid_metric(
        best_by_fluid,
        outdir,
        "04",
        "exergy_destruction",
        "04_exergy_destruction_vs_year.png",
        "\u3db2\u635f (kW)",
        lambda best: best["Ed_total_W"] / 1000.0,
        figsize=WIDE_FIGSIZE,
    )


def plot_lmtd_combined(best_by_fluid: dict[str, pd.DataFrame], outdir: Path) -> None:
    fig, (ax_hp, ax_lp) = plt.subplots(2, 1, figsize=WIDE_FIGSIZE_LMTD, sharex=True)
    points = None
    all_years = get_all_years(best_by_fluid)
    hp_values = []
    lp_values = []

    for fluid in TARGET_FLUIDS:
        best = best_by_fluid[fluid]
        integer_mask = get_integer_year_mask(best)
        label = get_fluid_display_name(fluid)

        lmtd_hp_plot = plot_raw_and_smooth(
            ax_hp,
            best["year"],
            smooth_display_series(best["lmtd_hp_K"], window=5),
            FLUID_COLORS[fluid],
            label,
            marker="^",
            linewidth=1.9,
            markersize=6.0,
        )
        hp_values.append(lmtd_hp_plot)
        lmtd_lp_plot = plot_raw_and_smooth(
            ax_lp,
            best["year"],
            smooth_display_series(best["lmtd_lp_K"], window=5),
            FLUID_COLORS[fluid],
            label,
            marker="^",
            linewidth=1.9,
            markersize=6.0,
        )
        lp_values.append(lmtd_lp_plot)

        if points is None:
            points = pd.DataFrame({"year": best.loc[integer_mask, "year"].reset_index(drop=True)})
        points[f"{label}_HP_K"] = lmtd_hp_plot[integer_mask]
        points[f"{label}_LP_K"] = lmtd_lp_plot[integer_mask]

    style_axes(ax_hp, ylabel="\u9ad8\u538b\u84b8\u53d1\u5668\u5bf9\u6570\u5e73\u5747\u6e29\u5dee (K)", xdata=all_years, zero_bottom=False)
    style_axes(ax_lp, ylabel="\u4f4e\u538b\u84b8\u53d1\u5668\u5bf9\u6570\u5e73\u5747\u6e29\u5dee (K)", xdata=all_years, zero_bottom=False)
    set_data_filled_ylim(ax_hp, hp_values, pad_ratio=0.08)
    set_data_filled_ylim(ax_lp, lp_values, pad_ratio=0.08)
    ax_hp.tick_params(axis="x", labelbottom=False)

    handles, labels = ax_hp.get_legend_handles_labels()
    desired_order = [get_fluid_display_name(fluid) for fluid in TARGET_FLUIDS]
    handles, labels = reorder_legend_by_label(handles, labels, desired_order)
    handles, labels = reorder_legend_for_row_major(handles, labels, LEGEND_NCOL)
    ax_hp.legend(
        handles,
        labels,
        frameon=False,
        ncol=LEGEND_NCOL,
        loc="upper right",
        bbox_to_anchor=(0.985, 0.985),
        columnspacing=0.9,
        handletextpad=0.7,
        fontsize=7.2,
        borderaxespad=0.2,
        labelspacing=0.35,
    )
    fig.subplots_adjust(left=0.13, right=0.985, top=0.98, bottom=0.10, hspace=0.12)
    fig.savefig(outdir / "06_07_lmtd_vs_year.png", bbox_inches="tight")
    plt.close(fig)
    export_plot_point_csv(outdir, "06_07", "lmtd", points)


def plot_selected_year_lmtd_comparisons(best_by_fluid: dict[str, pd.DataFrame], outdir: Path) -> None:
    component_labels = [label for label, _ in LMTD_COMPARE_COMPONENTS]
    x = np.arange(len(component_labels), dtype=float)
    width = 0.32

    for figure_prefix, year_value in zip(["09", "10"], LMTD_COMPARE_YEARS):
        fig, ax = plt.subplots(figsize=(6.8, 5.2))
        export_df = pd.DataFrame(
            {
                "year": [year_value] * len(component_labels),
                "component": component_labels,
            }
        )
        plotted_bars = []
        max_value = 0.0

        for fluid_idx, fluid in enumerate(LMTD_COMPARE_FLUIDS):
            best = best_by_fluid[fluid]
            year_idx = find_year_index(best, year_value)
            label = get_fluid_display_name(fluid)

            y_values = np.array(
                [
                    smooth_display_series(best[column], window=5)[year_idx]
                    for _, column in LMTD_COMPARE_COMPONENTS
                ],
                dtype=float,
            )
            export_df[f"{label}_K"] = y_values

            offset = (fluid_idx - (len(LMTD_COMPARE_FLUIDS) - 1) / 2.0) * width
            bars = ax.bar(
                x + offset,
                y_values,
                width=width,
                color=FLUID_COLORS[fluid],
                edgecolor="#404040",
                linewidth=0.8,
                alpha=0.95,
                label=label,
                zorder=3,
            )
            plotted_bars.append((bars, y_values))
            max_value = max(max_value, float(np.max(y_values)))

        label_pad = max(0.22, max_value * 0.018)
        for bars, y_values in plotted_bars:
            for bar, value in zip(bars, y_values):
                ax.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    value + label_pad,
                    f"{value:.2f}",
                    ha="center",
                    va="bottom",
                    fontsize=9.2,
                )

        ax.set_ylabel("对数平均温差 (K)")
        ax.set_xticks(x)
        ax.set_xticklabels(component_labels)
        ax.set_xlim(x[0] - 0.55, x[-1] + 0.55)
        ax.set_ylim(0, max_value + label_pad * 3.0)
        ax.set_title(f"第{int(year_value)}年", pad=8)
        ax.set_box_aspect(AXES_BOX_ASPECT)
        ax.yaxis.set_major_locator(MaxNLocator(nbins=6))
        ax.yaxis.set_minor_locator(NullLocator())
        ax.tick_params(axis="x", which="major", top=False, direction="in")
        ax.tick_params(axis="y", which="major", right=False, direction="in")
        ax.grid(axis="y", color="#D7D7D7", linewidth=0.8, alpha=0.75, zorder=0)
        for spine in ax.spines.values():
            spine.set_linewidth(1.2)
        ax.spines["top"].set_visible(True)
        ax.spines["right"].set_visible(True)
        ax.legend(frameon=False, loc="upper right")

        fig.subplots_adjust(left=0.14, right=0.98, top=0.90, bottom=0.14)
        outname = f"{figure_prefix}_r1234yf_r600a_lmtd_comparison_year_{int(year_value)}.png"
        fig.savefig(outdir / outname, bbox_inches="tight")
        plt.close(fig)
        export_plot_point_csv(
            outdir,
            figure_prefix,
            f"r1234yf_r600a_lmtd_comparison_year_{int(year_value)}",
            export_df,
        )




def main() -> None:
    args = parse_args()
    search_dir = resolve_search_dir(args.csv)
    csv_paths = resolve_fluid_csv_paths(search_dir)

    if args.outdir:
        outdir = Path(args.outdir).resolve()
    else:
        outdir = search_dir / f"figures_{DEFAULT_OUTPUT_NAME}"
    outdir.mkdir(parents=True, exist_ok=True)

    best_by_fluid = {}
    for fluid in TARGET_FLUIDS:
        _, best = load_and_filter(csv_paths[fluid])
        best_by_fluid[fluid] = best
    best_csv = save_best_csv(best_by_fluid, outdir)

    plot_net_power(best_by_fluid, outdir)
    plot_exergy_efficiency(best_by_fluid, outdir)
    plot_exergy_destruction(best_by_fluid, outdir)
    plot_lmtd_combined(best_by_fluid, outdir)
    plot_selected_year_lmtd_comparisons(best_by_fluid, outdir)

    print("Input files:")
    for fluid in TARGET_FLUIDS:
        print(f"  {get_fluid_display_name(fluid)}: {csv_paths[fluid]}")
    print(f"Combined best-by-year CSV: {best_csv}")
    print(f"Figure output directory: {outdir}")
    print("Selection rule: all curves use the feasible solution with the maximum net_output_kW for each year.")


if __name__ == "__main__":
    main()
