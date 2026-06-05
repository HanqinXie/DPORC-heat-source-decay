from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import AutoMinorLocator, MultipleLocator, NullLocator
from scipy.interpolate import PchipInterpolator

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent

# Only edit this one line. The input CSV, output folder name, and derived file names
# will all follow this filename automatically.
CSV_FILENAME = "R1234yf_40year_twostage_all_feasible_2026-04-18_20-16-01.csv"



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
        description="Generate paper-style plots from ORC transient CSV results."
    )
    parser.add_argument(
        "--csv",
        type=str,
        default=None,
        help="Optional override for the input CSV. By default, the script uses CSV_FILENAME at the top of this file.",
    )
    parser.add_argument(
        "--outdir",
        type=str,
        default=None,
        help="Output directory. If omitted, create figures_<csv_name>/ automatically.",
    )
    return parser.parse_args()


def find_latest_csv(workdir: Path) -> Path:
    patterns = [
        "R1234yf_40year_twostage_*.csv",
        "R1234yf_20year_twostage_*.csv",
        "R1234yf_20year_transient_*.csv",
        "R1234yf_40year_transient_*.csv",
    ]
    files = []
    for pattern in patterns:
        files.extend(workdir.glob(pattern))
    files = sorted({p.resolve() for p in files}, key=lambda p: p.stat().st_mtime)
    if not files:
        raise FileNotFoundError(
            f"No matching ORC CSV file found in {workdir}. "
            "Expected one of: R1234yf_40year_twostage_*.csv, "
            "R1234yf_20year_twostage_*.csv, "
            "R1234yf_20year_transient_*.csv, R1234yf_40year_transient_*.csv."
        )
    return files[-1]


def resolve_csv_path(csv_arg: str | None) -> Path:
    search_dirs = [SCRIPT_DIR, Path.cwd(), PROJECT_DIR]

    if csv_arg:
        raw_path = Path(csv_arg).expanduser()
        if raw_path.is_absolute() and raw_path.exists():
            return raw_path.resolve()

        candidate_paths = []
        if raw_path.is_absolute():
            candidate_paths.append(raw_path)
        else:
            candidate_paths.append((Path.cwd() / raw_path).resolve())
            candidate_paths.append((SCRIPT_DIR / raw_path).resolve())
            candidate_paths.append((PROJECT_DIR / raw_path).resolve())

        for candidate in candidate_paths:
            if candidate.exists():
                return candidate

        raise FileNotFoundError(
            f"CSV file not found: {csv_arg}. Checked: "
            + ", ".join(str(path) for path in candidate_paths)
        )

    if CSV_FILENAME:
        return resolve_csv_path(CSV_FILENAME)

    raise FileNotFoundError(
        "Please set CSV_FILENAME at the top of plot_orc_results.py, or pass --csv manually."
    )


def get_selected_source_name(csv_arg: str | None) -> str:
    selected = csv_arg if csv_arg else CSV_FILENAME
    if not selected:
        raise ValueError("CSV filename is empty. Please set CSV_FILENAME at the top of plot_orc_results.py.")
    return Path(selected).stem


def load_and_filter(csv_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
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

    source_curve = (
        df.groupby("year", as_index=False)["T_HS_in_K"]
        .first()
        .sort_values("year")
        .reset_index(drop=True)
    )
    best_idx = df.groupby("year")["net_output_kW"].idxmax()
    best = df.loc[best_idx].sort_values("year").reset_index(drop=True)
    return df, source_curve, best


def save_best_csv(best: pd.DataFrame, outdir: Path, source_name: str) -> Path:
    out_csv = outdir / f"{source_name}_best_by_net_output.csv"
    best.to_csv(out_csv, index=False, encoding="utf-8-sig")
    return out_csv


def get_integer_year_points(best: pd.DataFrame) -> pd.DataFrame:
    integer_mask = np.isclose(best["year"], np.round(best["year"]), atol=1e-9)
    return best.loc[integer_mask].copy().reset_index(drop=True)


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


def plot_raw_and_smooth(
    ax: plt.Axes,
    x,
    y,
    color: str,
    label: str,
    marker: str = "o",
    linewidth: float = 2.3,
    markersize: float = 3.8,
) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    y_mono, x_dense, y_dense, _ = smooth_xy(x, y)
    ax.plot(x_dense, y_dense, color=color, linewidth=linewidth, label=label)
    integer_mask = np.isclose(x, np.round(x), atol=1e-9)
    ax.plot(
        x[integer_mask],
        y_mono[integer_mask],
        linestyle="none",
        marker=marker,
        markersize=markersize,
        markerfacecolor="white",
        markeredgewidth=1.0,
        color=color,
    )
    return y_mono


def plot_step_series(
    ax: plt.Axes,
    x,
    y,
    color: str,
    label: str,
    marker: str = "o",
    linewidth: float = 2.0,
    markersize: float = 3.0,
) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    ax.step(x, y, where="post", color=color, linewidth=linewidth, label=label, zorder=2.0)
    ax.plot(
        x,
        y,
        linestyle="none",
        marker=marker,
        markersize=markersize,
        markerfacecolor="white",
        markeredgewidth=1.0,
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
    ax.xaxis.set_major_locator(MultipleLocator(5.0))
    ax.xaxis.set_minor_locator(AutoMinorLocator(2))
    ax.yaxis.set_minor_locator(AutoMinorLocator(2))
    ax.tick_params(axis="x", which="major", top=False, direction="in")
    ax.tick_params(axis="x", which="minor", top=False, direction="in")
    ax.tick_params(axis="y", which="major", right=False, direction="in")
    ax.tick_params(axis="y", which="minor", right=False, direction="in")
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


def plot_temperature(source_curve: pd.DataFrame, outdir: Path) -> None:
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    x = source_curve["year"].to_numpy(dtype=float)
    y = (source_curve["T_HS_in_K"] - 273.15).to_numpy(dtype=float)
    temp_plot, x_dense, y_dense, _ = smooth_xy(x, y)
    color = "#A23E48"
    state_years = np.arange(0.0, 41.0, 5.0)
    state_point_mask = np.any(np.isclose(x[:, None], state_years[None, :], atol=1e-9), axis=1)

    ax.plot(x_dense, y_dense, color=color, linewidth=2.3, label="\u70ed\u6e90\u6e29\u5ea6")
    ax.plot(
        x[state_point_mask],
        temp_plot[state_point_mask],
        linestyle="none",
        marker="^",
        markersize=6.4,
        markerfacecolor=color,
        markeredgecolor=color,
        markeredgewidth=1.1,
        color=color,
    )
    style_axes(ax, ylabel="\u70ed\u6e90\u5165\u53e3\u6e29\u5ea6 (\u00b0C)", xdata=source_curve["year"])
    x_span = float(x.max() - x.min())
    x_pad = max(0.5, 0.03 * x_span) if x_span > 0 else 0.5
    ax.set_xlim(x.min() - x_pad, x.max() + x_pad)
    ax.set_box_aspect(1.0 / 1.2)
    ax.xaxis.set_minor_locator(NullLocator())
    ax.yaxis.set_minor_locator(NullLocator())
    ax.set_ylim(110, 160)
    fig.subplots_adjust(left=0.12, right=0.98, top=0.98, bottom=0.12)
    fig.savefig(outdir / "01_heat_source_temperature_vs_year.png", bbox_inches="tight")
    plt.close(fig)
    state_points = source_curve.loc[state_point_mask].copy().reset_index(drop=True)
    points = pd.DataFrame(
        {
            "year": state_points["year"],
            "heat_source_temperature_C": temp_plot[state_point_mask],
        }
    )
    export_plot_point_csv(outdir, "01", "heat_source_temperature", points)


def plot_net_power(best: pd.DataFrame, outdir: Path) -> None:
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    net_output_plot = plot_raw_and_smooth(ax, best["year"], best["net_output_kW"], "#005F73", "\u51c0\u8f93\u51fa\u529f")
    style_axes(ax, ylabel="\u51c0\u8f93\u51fa\u529f (kW)", xdata=best["year"], zero_bottom=True)
    save_figure(fig, outdir / "02_net_output_vs_year.png")
    integer_mask = np.isclose(best["year"], np.round(best["year"]), atol=1e-9)
    points = pd.DataFrame({"year": best.loc[integer_mask, "year"], "net_output_kW": net_output_plot[integer_mask]})
    export_plot_point_csv(outdir, "02", "net_output", points)


def plot_exergy_efficiency(best: pd.DataFrame, outdir: Path) -> None:
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    eta_ex_plot = plot_raw_and_smooth(ax, best["year"], best["eta_ex_percent"], "#CA6702", "\u3db2\u6548\u7387")
    style_axes(ax, ylabel="\u3db2\u6548\u7387 (%)", xdata=best["year"])
    ax.set_ylim(bottom=20)
    save_figure(fig, outdir / "03_exergy_efficiency_vs_year.png")
    integer_mask = np.isclose(best["year"], np.round(best["year"]), atol=1e-9)
    points = pd.DataFrame({"year": best.loc[integer_mask, "year"], "eta_ex_percent": eta_ex_plot[integer_mask]})
    export_plot_point_csv(outdir, "03", "exergy_efficiency", points)


def plot_exergy_destruction(best: pd.DataFrame, outdir: Path) -> None:
    fig, ax = plt.subplots(figsize=(9.0, 5.2))
    series = [(
        "\u603b\u3db2\u635f", "Ed_total_W", "#7B2CBF", 2.8
    )]
    plotted_series = {}
    for _, col, color, lw in series:
        plotted_series[col] = plot_raw_and_smooth(
            ax, best["year"], best[col] / 1000.0, color, "_nolegend_", linewidth=lw, markersize=3.2
        )
    style_axes(ax, ylabel="\u3db2\u635f (kW)", xdata=best["year"], zero_bottom=True)
    save_figure(fig, outdir / "04_exergy_destruction_vs_year.png")
    integer_best = get_integer_year_points(best)
    points = pd.DataFrame({"year": integer_best["year"]})
    integer_mask = np.isclose(best["year"], np.round(best["year"]), atol=1e-9)
    for _, col, _, _ in series:
        points[f"{col}_kW"] = plotted_series[col][integer_mask]
    export_plot_point_csv(outdir, "04", "exergy_destruction", points)


def plot_exergy_ratio(best: pd.DataFrame, outdir: Path) -> None:
    fig, ax = plt.subplots(figsize=(9.0, 6.0))
    x = best["year"].to_numpy(dtype=float)
    integer_best = get_integer_year_points(best)
    if {"ratio_Ede_pre_percent", "ratio_Ede_hp_percent", "ratio_Ede_lp_percent"}.issubset(best.columns):
        series = [
            ("ratio_Ede_pre_percent", "\u9884\u70ed\u5668", "#8E2C1C"),
            ("ratio_Ede_hp_percent", "\u9ad8\u538b\u84b8\u53d1\u5668", "#D1493F"),
            ("ratio_Ede_lp_percent", "\u4f4e\u538b\u84b8\u53d1\u5668", "#F28E2B"),
            ("ratio_Edt_h_percent", "\u9ad8\u538b\u900f\u5e73", "#2F5D73"),
            ("ratio_Edt_l_percent", "\u4f4e\u538b\u900f\u5e73", "#58A6B6"),
            ("ratio_Edp_1_percent", "\u4f4e\u538b\u5de5\u8d28\u6cf5", "#4E6E58"),
            ("ratio_Edp_2_percent", "\u9ad8\u538b\u5de5\u8d28\u6cf5", "#8AA17B"),
            ("ratio_Edc_plus_Edmix_percent", "\u51b7\u51dd\u5668", "#E7AE72"),
        ]
        raw_values = {
            "ratio_Ede_pre_percent": best["ratio_Ede_pre_percent"].to_numpy(dtype=float),
            "ratio_Ede_hp_percent": best["ratio_Ede_hp_percent"].to_numpy(dtype=float),
            "ratio_Ede_lp_percent": best["ratio_Ede_lp_percent"].to_numpy(dtype=float),
            "ratio_Edt_h_percent": best["ratio_Edt_h_percent"].to_numpy(dtype=float),
            "ratio_Edt_l_percent": best["ratio_Edt_l_percent"].to_numpy(dtype=float),
            "ratio_Edp_1_percent": best["ratio_Edp_1_percent"].to_numpy(dtype=float),
            "ratio_Edp_2_percent": best["ratio_Edp_2_percent"].to_numpy(dtype=float),
            "ratio_Edc_plus_Edmix_percent": (
                best["ratio_Edc_percent"].to_numpy(dtype=float)
                + best["ratio_Edmix_percent"].to_numpy(dtype=float)
            ),
        }
        legend_cols = 4
        points = pd.DataFrame({
            "year": integer_best["year"],
            "ratio_Ede_pre_percent": integer_best["ratio_Ede_pre_percent"],
            "ratio_Ede_hp_percent": integer_best["ratio_Ede_hp_percent"],
            "ratio_Ede_lp_percent": integer_best["ratio_Ede_lp_percent"],
            "ratio_Edt_h_percent": integer_best["ratio_Edt_h_percent"],
            "ratio_Edt_l_percent": integer_best["ratio_Edt_l_percent"],
            "ratio_Edp_1_percent": integer_best["ratio_Edp_1_percent"],
            "ratio_Edp_2_percent": integer_best["ratio_Edp_2_percent"],
            "ratio_Edc_plus_Edmix_percent": integer_best["ratio_Edc_percent"] + integer_best["ratio_Edmix_percent"],
        })
    elif {"ratio_Ede_hp_percent", "ratio_Ede_lp_percent"}.issubset(best.columns):
        series = [
            ("ratio_Ede_hp_percent", "高压蒸发器", "#D1493F"),
            ("ratio_Ede_lp_percent", "低压蒸发器", "#F28E2B"),
            ("ratio_Edt_h_percent", "高压透平", "#2F5D73"),
            ("ratio_Edt_l_percent", "低压透平", "#58A6B6"),
            ("ratio_Edp_1_percent", "低压工质泵", "#4E6E58"),
            ("ratio_Edp_2_percent", "高压工质泵", "#8AA17B"),
            ("ratio_Edc_plus_Edmix_percent", "冷凝器", "#E7AE72"),
        ]
        raw_values = {
            "ratio_Ede_hp_percent": best["ratio_Ede_hp_percent"].to_numpy(dtype=float),
            "ratio_Ede_lp_percent": best["ratio_Ede_lp_percent"].to_numpy(dtype=float),
            "ratio_Edt_h_percent": best["ratio_Edt_h_percent"].to_numpy(dtype=float),
            "ratio_Edt_l_percent": best["ratio_Edt_l_percent"].to_numpy(dtype=float),
            "ratio_Edp_1_percent": best["ratio_Edp_1_percent"].to_numpy(dtype=float),
            "ratio_Edp_2_percent": best["ratio_Edp_2_percent"].to_numpy(dtype=float),
            "ratio_Edc_plus_Edmix_percent": (
                best["ratio_Edc_percent"].to_numpy(dtype=float)
                + best["ratio_Edmix_percent"].to_numpy(dtype=float)
            ),
        }
        legend_cols = 4
        points = pd.DataFrame({
            "year": integer_best["year"],
            "ratio_Ede_hp_percent": integer_best["ratio_Ede_hp_percent"],
            "ratio_Ede_lp_percent": integer_best["ratio_Ede_lp_percent"],
            "ratio_Edt_h_percent": integer_best["ratio_Edt_h_percent"],
            "ratio_Edt_l_percent": integer_best["ratio_Edt_l_percent"],
            "ratio_Edp_1_percent": integer_best["ratio_Edp_1_percent"],
            "ratio_Edp_2_percent": integer_best["ratio_Edp_2_percent"],
            "ratio_Edc_plus_Edmix_percent": integer_best["ratio_Edc_percent"] + integer_best["ratio_Edmix_percent"],
        })
    else:
        series = [
            ("ratio_Ede_percent", "\u84b8\u53d1\u5668", "#D1493F"),
            ("ratio_Edt_h_percent", "\u9ad8\u538b\u900f\u5e73", "#2F5D73"),
            ("ratio_Edt_l_percent", "\u4f4e\u538b\u900f\u5e73", "#58A6B6"),
            ("ratio_Edp_1_percent", "\u4f4e\u538b\u5de5\u8d28\u6cf5", "#4E6E58"),
            ("ratio_Edp_2_percent", "\u9ad8\u538b\u5de5\u8d28\u6cf5", "#8AA17B"),
            ("ratio_Edc_plus_Edmix_percent", "\u51b7\u51dd\u5668", "#E7AE72"),
        ]
        raw_values = {
            "ratio_Ede_percent": best["ratio_Ede_percent"].to_numpy(dtype=float),
            "ratio_Edt_h_percent": best["ratio_Edt_h_percent"].to_numpy(dtype=float),
            "ratio_Edt_l_percent": best["ratio_Edt_l_percent"].to_numpy(dtype=float),
            "ratio_Edp_1_percent": best["ratio_Edp_1_percent"].to_numpy(dtype=float),
            "ratio_Edp_2_percent": best["ratio_Edp_2_percent"].to_numpy(dtype=float),
            "ratio_Edc_plus_Edmix_percent": (
                best["ratio_Edc_percent"].to_numpy(dtype=float)
                + best["ratio_Edmix_percent"].to_numpy(dtype=float)
            ),
        }
        legend_cols = 3
        points = pd.DataFrame({
            "year": integer_best["year"],
            "ratio_Ede_percent": integer_best["ratio_Ede_percent"],
            "ratio_Edt_h_percent": integer_best["ratio_Edt_h_percent"],
            "ratio_Edt_l_percent": integer_best["ratio_Edt_l_percent"],
            "ratio_Edp_1_percent": integer_best["ratio_Edp_1_percent"],
            "ratio_Edp_2_percent": integer_best["ratio_Edp_2_percent"],
            "ratio_Edc_plus_Edmix_percent": integer_best["ratio_Edc_percent"] + integer_best["ratio_Edmix_percent"],
        })

    x_dense, monotonic_yearly, y_dense = build_monotonic_composition(x, series, raw_values, points=400)

    points = pd.DataFrame({"year": integer_best["year"]})
    integer_mask = np.isclose(x, np.round(x), atol=1e-9)
    for col, _, _ in series:
        points[col] = monotonic_yearly[col][integer_mask]

    stack_handles = ax.stackplot(
        x_dense,
        y_dense,
        labels=[label for _, label, _ in series],
        colors=[color for _, _, color in series],
        alpha=0.92,
        linewidth=0.5,
        edgecolor="#FCFCFC",
    )
    for year in x:
        ax.axvline(year, color="#FFFFFF", linewidth=0.35, alpha=0.22, zorder=0)

    style_axes(ax, ylabel="\u3db2\u635f\u5360\u6bd4 (%)", xdata=best["year"], zero_bottom=True)
    ax.set_ylim(0, 100)
    legend_labels = [label for _, label, _ in series]
    legend_handles, legend_labels = reorder_legend_for_row_major(stack_handles, legend_labels, legend_cols)
    fig.legend(
        legend_handles,
        legend_labels,
        frameon=False,
        ncol=legend_cols,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.015),
        columnspacing=1.25,
        handletextpad=0.7,
    )
    fig.subplots_adjust(left=0.10, right=0.98, top=0.98, bottom=0.19)
    fig.savefig(outdir / "05_exergy_ratio_vs_year.png", bbox_inches="tight")
    plt.close(fig)
    export_plot_point_csv(outdir, "05", "exergy_ratio", points)


def plot_lmtd_combined(best: pd.DataFrame, outdir: Path) -> None:
    fig, ax = plt.subplots(figsize=(8.8, 5.0))
    lmtd_hp_plot = plot_raw_and_smooth(
        ax,
        best["year"],
        smooth_display_series(best["lmtd_hp_K"], window=5),
        "#8D0801",
        "\u9ad8\u538b\u84b8\u53d1\u5668\u5bf9\u6570\u5e73\u5747\u6e29\u5dee",
        marker="o",
    )
    lmtd_lp_plot = plot_raw_and_smooth(
        ax,
        best["year"],
        smooth_display_series(best["lmtd_lp_K"], window=5),
        "#005F73",
        "\u4f4e\u538b\u84b8\u53d1\u5668\u5bf9\u6570\u5e73\u5747\u6e29\u5dee",
        marker="s",
        linewidth=2.0,
    )
    style_axes(ax, ylabel="\u5bf9\u6570\u5e73\u5747\u6e29\u5dee (K)", xdata=best["year"], zero_bottom=True)
    ax.legend(frameon=False)
    save_figure(fig, outdir / "06_07_lmtd_vs_year.png")
    integer_mask = np.isclose(best["year"], np.round(best["year"]), atol=1e-9)
    points = pd.DataFrame({
        "year": best.loc[integer_mask, "year"],
        "lmtd_hp_K": lmtd_hp_plot[integer_mask],
        "lmtd_lp_K": lmtd_lp_plot[integer_mask],
    })
    export_plot_point_csv(outdir, "06_07", "lmtd", points)




def main() -> None:
    args = parse_args()
    csv_path = resolve_csv_path(args.csv)
    source_name = get_selected_source_name(args.csv)

    if args.outdir:
        outdir = Path(args.outdir).resolve()
    else:
        outdir = csv_path.parent / f"figures_{source_name}"
    outdir.mkdir(parents=True, exist_ok=True)

    _, source_curve, best = load_and_filter(csv_path)
    best_csv = save_best_csv(best, outdir, source_name)

    plot_temperature(source_curve, outdir)
    plot_net_power(best, outdir)
    plot_exergy_efficiency(best, outdir)
    plot_exergy_destruction(best, outdir)
    plot_exergy_ratio(best, outdir)
    plot_lmtd_combined(best, outdir)

    print(f"Input file: {csv_path}")
    print(f"Best-by-year CSV: {best_csv}")
    print(f"Figure output directory: {outdir}")
    print("Selection rule: heat-source temperature uses the year-level source value; all other curves use the feasible solution with the maximum net_output_kW for each year.")


if __name__ == "__main__":
    main()
