from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle
from matplotlib.ticker import AutoMinorLocator, MultipleLocator
from scipy.interpolate import PchipInterpolator

# Default CSV file. Set to None to auto-detect the latest transient CSV in the current directory.
CSV_FILENAME = "R1234yf_20year_transient_2026-04-18_11-34-25.csv"


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
        help="Input CSV path. If omitted, use the latest R1234yf_40year_transient_*.csv in the current directory.",
    )
    parser.add_argument(
        "--outdir",
        type=str,
        default=None,
        help="Output directory. If omitted, create figures_<csv_name>/ automatically.",
    )
    return parser.parse_args()


def find_latest_csv(workdir: Path) -> Path:
    files = sorted(workdir.glob("R1234yf_40year_transient_*.csv"), key=lambda p: p.stat().st_mtime)
    if not files:
        raise FileNotFoundError("No R1234yf_40year_transient_*.csv file found in the current directory.")
    return files[-1]


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


def smooth_xy(x, y, points: int = 400):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    x_dense = np.linspace(x.min(), x.max(), points)
    y_dense = PchipInterpolator(x, y)(x_dense)
    return x_dense, y_dense


def smooth_display_series(y, window: int = 5):
    """Light display-only smoothing: median then mean rolling filters."""
    s = pd.Series(np.asarray(y, dtype=float))
    s = s.rolling(window=window, center=True, min_periods=1).median()
    s = s.rolling(window=window, center=True, min_periods=1).mean()
    return s.to_numpy(dtype=float)


def plot_raw_and_smooth(
    ax: plt.Axes,
    x,
    y,
    color: str,
    label: str,
    marker: str = "o",
    linewidth: float = 2.3,
    markersize: float = 3.8,
) -> None:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    x_dense, y_dense = smooth_xy(x, y)
    ax.plot(x_dense, y_dense, color=color, linewidth=linewidth, label=label)
    integer_mask = np.isclose(x, np.round(x), atol=1e-9)
    ax.plot(
        x[integer_mask],
        y[integer_mask],
        linestyle="none",
        marker=marker,
        markersize=markersize,
        markerfacecolor="white",
        markeredgewidth=1.0,
        color=color,
    )


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


def plot_temperature(best: pd.DataFrame, outdir: Path) -> None:
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    plot_raw_and_smooth(ax, best["year"], best["T_HS_in_K"] - 273.15, "#A23E48", "\u70ed\u6e90\u6e29\u5ea6")
    style_axes(ax, ylabel="\u70ed\u6e90\u5165\u53e3\u6e29\u5ea6 (\u00b0C)", xdata=best["year"])
    ax.set_ylim(bottom=80)
    save_figure(fig, outdir / "01_heat_source_temperature_vs_year.png")
    integer_best = get_integer_year_points(best)
    points = pd.DataFrame(
        {
            "year": integer_best["year"],
            "heat_source_temperature_C": integer_best["T_HS_in_K"] - 273.15,
        }
    )
    export_plot_point_csv(outdir, "01", "heat_source_temperature", points)


def plot_net_power(best: pd.DataFrame, outdir: Path) -> None:
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    plot_raw_and_smooth(ax, best["year"], best["net_output_kW"], "#005F73", "\u51c0\u8f93\u51fa\u529f")
    style_axes(ax, ylabel="\u51c0\u8f93\u51fa\u529f (kW)", xdata=best["year"], zero_bottom=True)
    save_figure(fig, outdir / "02_net_output_vs_year.png")
    points = get_integer_year_points(best)[["year", "net_output_kW"]].copy()
    export_plot_point_csv(outdir, "02", "net_output", points)


def plot_exergy_efficiency(best: pd.DataFrame, outdir: Path) -> None:
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    plot_raw_and_smooth(ax, best["year"], best["eta_ex_percent"], "#CA6702", "\u3db2\u6548\u7387")
    style_axes(ax, ylabel="\u3db2\u6548\u7387 (%)", xdata=best["year"])
    ax.set_ylim(bottom=20)
    save_figure(fig, outdir / "03_exergy_efficiency_vs_year.png")
    points = get_integer_year_points(best)[["year", "eta_ex_percent"]].copy()
    export_plot_point_csv(outdir, "03", "exergy_efficiency", points)


def plot_exergy_destruction(best: pd.DataFrame, outdir: Path) -> None:
    fig, ax = plt.subplots(figsize=(9.0, 5.2))
    series = [(
        "\u603b\u3db2\u635f", "Ed_total_W", "#7B2CBF", 2.8
    )]
    for _, col, color, lw in series:
        plot_raw_and_smooth(ax, best["year"], best[col] / 1000.0, color, "_nolegend_", linewidth=lw, markersize=3.2)
    style_axes(ax, ylabel="\u3db2\u635f (kW)", xdata=best["year"], zero_bottom=True)
    save_figure(fig, outdir / "04_exergy_destruction_vs_year.png")
    integer_best = get_integer_year_points(best)
    points = pd.DataFrame({"year": integer_best["year"]})
    for _, col, _, _ in series:
        points[f"{col}_kW"] = integer_best[col] / 1000.0
    export_plot_point_csv(outdir, "04", "exergy_destruction", points)


def plot_exergy_ratio(best: pd.DataFrame, outdir: Path) -> None:
    fig, ax = plt.subplots(figsize=(9.2, 5.4))
    x = best["year"].to_numpy(dtype=float)
    x_dense = np.linspace(x.min(), x.max(), 400)
    integer_best = get_integer_year_points(best)
    if {"ratio_Ede_pre_percent", "ratio_Ede_hp_percent", "ratio_Ede_lp_percent"}.issubset(best.columns):
        y = np.vstack([
            PchipInterpolator(x, best["ratio_Ede_pre_percent"].to_numpy(dtype=float))(x_dense),
            PchipInterpolator(x, best["ratio_Ede_hp_percent"].to_numpy(dtype=float))(x_dense),
            PchipInterpolator(x, best["ratio_Ede_lp_percent"].to_numpy(dtype=float))(x_dense),
            PchipInterpolator(x, best["ratio_Edt_h_percent"].to_numpy(dtype=float))(x_dense),
            PchipInterpolator(x, best["ratio_Edt_l_percent"].to_numpy(dtype=float))(x_dense),
            PchipInterpolator(x, best["ratio_Edp_1_percent"].to_numpy(dtype=float))(x_dense),
            PchipInterpolator(x, best["ratio_Edp_2_percent"].to_numpy(dtype=float))(x_dense),
            PchipInterpolator(x, best["ratio_Edc_percent"].to_numpy(dtype=float))(x_dense) +
            PchipInterpolator(x, best["ratio_Edmix_percent"].to_numpy(dtype=float))(x_dense),
        ])
        labels = [
            "\u9884\u70ed\u5668", "\u9ad8\u538b\u84b8\u53d1\u5668", "\u4f4e\u538b\u84b8\u53d1\u5668",
            "\u9ad8\u538b\u900f\u5e73", "\u4f4e\u538b\u900f\u5e73", "\u4f4e\u538b\u5de5\u8d28\u6cf5",
            "\u9ad8\u538b\u5de5\u8d28\u6cf5", "\u51b7\u51dd\u5668"
        ]
        colors = ["#8E2C1C", "#D1493F", "#F28E2B", "#2F5D73", "#58A6B6", "#4E6E58", "#8AA17B", "#E7AE72"]
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
        y = np.vstack([
            PchipInterpolator(x, best["ratio_Ede_hp_percent"].to_numpy(dtype=float))(x_dense),
            PchipInterpolator(x, best["ratio_Ede_lp_percent"].to_numpy(dtype=float))(x_dense),
            PchipInterpolator(x, best["ratio_Edt_h_percent"].to_numpy(dtype=float))(x_dense),
            PchipInterpolator(x, best["ratio_Edt_l_percent"].to_numpy(dtype=float))(x_dense),
            PchipInterpolator(x, best["ratio_Edp_1_percent"].to_numpy(dtype=float))(x_dense),
            PchipInterpolator(x, best["ratio_Edp_2_percent"].to_numpy(dtype=float))(x_dense),
            PchipInterpolator(x, best["ratio_Edc_percent"].to_numpy(dtype=float))(x_dense) +
            PchipInterpolator(x, best["ratio_Edmix_percent"].to_numpy(dtype=float))(x_dense),
        ])
        labels = [
            "高压蒸发器", "低压蒸发器", "高压透平", "低压透平",
            "低压工质泵", "高压工质泵", "冷凝器"
        ]
        colors = ["#D1493F", "#F28E2B", "#2F5D73", "#58A6B6", "#4E6E58", "#8AA17B", "#E7AE72"]
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
        y = np.vstack([
            PchipInterpolator(x, best["ratio_Ede_percent"].to_numpy(dtype=float))(x_dense),
            PchipInterpolator(x, best["ratio_Edt_h_percent"].to_numpy(dtype=float))(x_dense),
            PchipInterpolator(x, best["ratio_Edt_l_percent"].to_numpy(dtype=float))(x_dense),
            PchipInterpolator(x, best["ratio_Edp_1_percent"].to_numpy(dtype=float))(x_dense),
            PchipInterpolator(x, best["ratio_Edp_2_percent"].to_numpy(dtype=float))(x_dense),
            PchipInterpolator(x, best["ratio_Edc_percent"].to_numpy(dtype=float))(x_dense) +
            PchipInterpolator(x, best["ratio_Edmix_percent"].to_numpy(dtype=float))(x_dense),
        ])
        labels = [
            "\u84b8\u53d1\u5668", "\u9ad8\u538b\u900f\u5e73", "\u4f4e\u538b\u900f\u5e73",
            "\u4f4e\u538b\u5de5\u8d28\u6cf5", "\u9ad8\u538b\u5de5\u8d28\u6cf5", "\u51b7\u51dd\u5668"
        ]
        colors = ["#D1493F", "#2F5D73", "#58A6B6", "#4E6E58", "#8AA17B", "#E7AE72"]
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
    y = np.clip(y, 0, None)
    y = y / y.sum(axis=0) * 100.0
    stack_handles = ax.stackplot(x_dense, y, labels=labels, colors=colors, alpha=0.9)
    for year in x:
        ax.axvline(year, color="#FFFFFF", linewidth=0.35, alpha=0.28, zorder=0)
    style_axes(ax, ylabel="\u3db2\u635f\u5360\u6bd4 (%)", xdata=best["year"], zero_bottom=True)
    ax.set_ylim(0, 100)
    legend_bg = Rectangle(
        (0.36, 0.885),
        0.64,
        0.115,
        transform=ax.transAxes,
        facecolor="white",
        edgecolor="none",
        zorder=3.5,
    )
    ax.add_patch(legend_bg)
    legend_handles, legend_labels = reorder_legend_for_row_major(stack_handles, labels, legend_cols)
    legend = ax.legend(
        legend_handles,
        legend_labels,
        frameon=False,
        ncol=legend_cols,
        loc="upper left",
        bbox_to_anchor=(0.42, 0.992),
        borderaxespad=0.0,
        columnspacing=1.55,
        handletextpad=0.8,
    )
    legend.set_zorder(4.0)
    save_figure(fig, outdir / "05_exergy_ratio_vs_year.png")
    export_plot_point_csv(outdir, "05", "exergy_ratio", points)


def plot_lmtd_combined(best: pd.DataFrame, outdir: Path) -> None:
    fig, ax = plt.subplots(figsize=(8.8, 5.0))
    lmtd_hp_plot = smooth_display_series(best["lmtd_hp_K"], window=5)
    lmtd_lp_plot = smooth_display_series(best["lmtd_lp_K"], window=5)
    plot_raw_and_smooth(ax, best["year"], lmtd_hp_plot, "#8D0801", "\u9ad8\u538b\u84b8\u53d1\u5668\u5bf9\u6570\u5e73\u5747\u6e29\u5dee", marker="o")
    plot_raw_and_smooth(ax, best["year"], lmtd_lp_plot, "#005F73", "\u4f4e\u538b\u84b8\u53d1\u5668\u5bf9\u6570\u5e73\u5747\u6e29\u5dee", marker="s", linewidth=2.0)
    style_axes(ax, ylabel="\u5bf9\u6570\u5e73\u5747\u6e29\u5dee (K)", xdata=best["year"], zero_bottom=True)
    ax.legend(frameon=False)
    save_figure(fig, outdir / "06_07_lmtd_vs_year.png")
    integer_best = get_integer_year_points(best)
    points = pd.DataFrame({
        "year": integer_best["year"],
        "lmtd_hp_K": integer_best["lmtd_hp_K"],
        "lmtd_lp_K": integer_best["lmtd_lp_K"],
    })
    export_plot_point_csv(outdir, "06_07", "lmtd", points)




def main() -> None:
    args = parse_args()
    workdir = Path.cwd()
    if args.csv:
        csv_path = Path(args.csv).resolve()
    elif CSV_FILENAME:
        csv_path = (workdir / CSV_FILENAME).resolve()
    else:
        csv_path = find_latest_csv(workdir)
    source_name = csv_path.stem

    if args.outdir:
        outdir = Path(args.outdir).resolve()
    else:
        outdir = workdir / f"figures_{source_name}"
    outdir.mkdir(parents=True, exist_ok=True)

    _, best = load_and_filter(csv_path)
    best_csv = save_best_csv(best, outdir, source_name)

    plot_temperature(best, outdir)
    plot_net_power(best, outdir)
    plot_exergy_efficiency(best, outdir)
    plot_exergy_destruction(best, outdir)
    plot_exergy_ratio(best, outdir)
    plot_lmtd_combined(best, outdir)

    print(f"Input file: {csv_path}")
    print(f"Best-by-year CSV: {best_csv}")
    print(f"Figure output directory: {outdir}")
    print("Selection rule: choose the feasible solution with the maximum net_output_kW for each year.")


if __name__ == "__main__":
    main()
