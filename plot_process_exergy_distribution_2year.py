from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from matplotlib.ticker import MultipleLocator


SCRIPT_DIR = Path(__file__).resolve().parent

DEFAULT_INPUT_CSV = SCRIPT_DIR / "figures_9fluids_comparison" / "all_fluids_best_by_net_output.csv"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "figures_process_exergy_distribution_2year"
GRID_OUTPUT_PATH = DEFAULT_OUTPUT_DIR / "process_exergy_distribution_2year_3x3_grid.png"

OUTPUT_SIZE_SCALE = 1.25
SAVEFIG_DPI = int(round(300 * OUTPUT_SIZE_SCALE))
PROCESS_LABEL_FONT_SIZE = 24
AXIS_TICK_FONT_SIZE = PROCESS_LABEL_FONT_SIZE
ARROW_LABEL_FONT_SIZE = 24
AXIS_LABEL_FONT_SIZE = PROCESS_LABEL_FONT_SIZE
FLUID_TITLE_FONT_SIZE = 29
SUBFIGURE_LABEL_FONT_SIZE = int(round(120 * OUTPUT_SIZE_SCALE))
SUBFIGURE_LABEL_TOP_PADDING = int(round(16 * OUTPUT_SIZE_SCALE))
SUBFIGURE_LABEL_BOTTOM_PADDING = int(round(28 * OUTPUT_SIZE_SCALE))
TIMES_NEW_ROMAN_FONT_PATH = Path("C:/Windows/Fonts/times.ttf")
X_AXIS_VISIBLE_MIN_C = 113.0
X_AXIS_TICK_START_C = 115.0

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

PROCESS_SPECS = [
    {
        "column": "ratio_unused_total_percent",
        "label": "热源未利用㶲损",
        "color": "#C7B8F5",
        "text_color": "#1F1F1F",
        "xfrac": 0.27,
        "label_mode": "inside",
    },
    {
        "column": "ratio_Ede_total_percent",
        "label": "蒸发器换热㶲损",
        "color": "#F2B447",
        "text_color": "#1F1F1F",
        "xfrac": 0.28,
        "label_mode": "inside",
    },
    {
        "column": "ratio_Edt_total_percent",
        "label": "透平㶲损",
        "color": "#4C78A8",
        "text_color": "white",
        "xfrac": 0.26,
        "label_mode": "inside",
    },
    {
        "column": "ratio_Edc_total_percent",
        "label": "冷凝器㶲损",
        "color": "#72B7B2",
        "text_color": "#1F1F1F",
        "xfrac": 0.20,
        "label_mode": "inside",
    },
    {
        "column": "ratio_Edp_total_percent",
        "label": "泵㶲损",
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
        "savefig.dpi": SAVEFIG_DPI,
        "axes.labelsize": AXIS_LABEL_FONT_SIZE,
        "axes.labelweight": "bold",
        "xtick.labelsize": AXIS_TICK_FONT_SIZE,
        "ytick.labelsize": AXIS_TICK_FONT_SIZE,
    }
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot process-wise exergy destruction distributions using a 2-year sampling step and export a 3x3 grid."
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
        default=None,
        help="Output directory for process exergy distribution figures. Defaults to figures_process_exergy_distribution_<year-step>year.",
    )
    parser.add_argument(
        "--year-step",
        type=int,
        default=2,
        help="Sampling step in years. Default is 2.",
    )
    return parser.parse_args()


def style_axes(ax: plt.Axes, x_c: np.ndarray) -> None:
    ax.set_xlabel("热源入口温度（℃）", fontsize=AXIS_LABEL_FONT_SIZE, fontweight="bold", labelpad=6)
    ax.set_ylabel("㶲损占比（%）", fontsize=AXIS_LABEL_FONT_SIZE, fontweight="bold", labelpad=6)
    ax.set_xlim(X_AXIS_VISIBLE_MIN_C, float(x_c.max()))
    ax.set_ylim(0.0, 100.0)
    ax.margins(x=0)
    ax.set_xticks(np.arange(X_AXIS_TICK_START_C, float(x_c.max()) + 0.1, 5.0))
    ax.yaxis.set_major_locator(MultipleLocator(20.0))
    ax.tick_params(axis="both", which="major", direction="in", length=4, width=1.0, pad=8)
    for tick_label in ax.get_xticklabels() + ax.get_yticklabels():
        tick_label.set_fontsize(AXIS_TICK_FONT_SIZE)
        tick_label.set_fontweight("bold")
    for spine in ax.spines.values():
        spine.set_linewidth(1.2)
    add_bottom_axis_break(ax)


def add_bottom_axis_break(ax: plt.Axes) -> None:
    x0 = 0.018
    slash_width = 0.008
    slash_gap = 0.006
    slash_y0 = -0.020
    slash_y1 = 0.030
    mask_x0 = x0 - 0.006
    mask_x1 = x0 + 2.0 * slash_width + slash_gap + 0.006

    ax.plot(
        [mask_x0, mask_x1],
        [0.0, 0.0],
        transform=ax.transAxes,
        color=PROCESS_SPECS[0]["color"],
        linewidth=3.2,
        solid_capstyle="butt",
        clip_on=True,
        zorder=5,
    )
    for offset in (0.0, slash_width + slash_gap):
        ax.plot(
            [x0 + offset, x0 + offset + slash_width],
            [slash_y0, slash_y1],
            transform=ax.transAxes,
            color="black",
            linewidth=1.2,
            solid_capstyle="butt",
            clip_on=False,
            zorder=6,
        )


def place_inside_label(
    ax: plt.Axes,
    x: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    text: str,
    xfrac: float,
    text_color: str,
) -> None:
    span = float(x[-1] - x[0])
    x_pos = float(x[0] + span * xfrac)
    x_pos = float(np.clip(x_pos, x[0] + span * 0.12, x[-1] - span * 0.12))
    lower_y = float(np.interp(x_pos, x, lower))
    upper_y = float(np.interp(x_pos, x, upper))
    ymid = 0.5 * (lower_y + upper_y)
    ax.text(
        x_pos,
        ymid,
        text,
        color=text_color,
        fontsize=PROCESS_LABEL_FONT_SIZE,
        fontweight="bold",
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
    span = float(x[-1] - x[0])
    x_pos = float(x[0] + span * xfrac)
    x_pos = float(np.clip(x_pos, x[0] + span * 0.03, x[-1] - span * 0.03))
    lower_y = float(np.interp(x_pos, x, lower))
    upper_y = float(np.interp(x_pos, x, upper))
    ymid = 0.5 * (lower_y + upper_y)
    ax.annotate(
        text,
        xy=(x_pos, ymid),
        xycoords="data",
        xytext=text_axes,
        textcoords="axes fraction",
        ha="center",
        va="center",
        color=text_color,
        fontsize=ARROW_LABEL_FONT_SIZE,
        fontweight="bold",
        arrowprops={"arrowstyle": "->", "color": text_color, "lw": 1.0},
    )


def build_process_columns(plot_df: pd.DataFrame) -> pd.DataFrame:
    ein_w = plot_df["net_output_kW"].to_numpy(dtype=float) * 1000.0 / (
        plot_df["eta_ex_percent"].to_numpy(dtype=float) / 100.0
    )
    ed_total_w = plot_df["Ed_total_W"].to_numpy(dtype=float)
    net_output_w = plot_df["net_output_kW"].to_numpy(dtype=float) * 1000.0
    unused_w = ein_w - ed_total_w - net_output_w
    total_loss_w = ed_total_w + unused_w

    plot_df = plot_df.copy()
    plot_df["ratio_unused_total_percent"] = unused_w / total_loss_w * 100.0
    plot_df["ratio_Ede_total_percent"] = plot_df["ratio_Ede_percent"].to_numpy(dtype=float) * ed_total_w / total_loss_w
    plot_df["ratio_Edt_total_percent"] = plot_df["ratio_Edt_percent"].to_numpy(dtype=float) * ed_total_w / total_loss_w
    plot_df["ratio_Edc_total_percent"] = (
        (plot_df["ratio_Edc_percent"].to_numpy(dtype=float) + plot_df["ratio_Edmix_percent"].to_numpy(dtype=float))
        * ed_total_w
        / total_loss_w
    )
    plot_df["ratio_Edp_total_percent"] = plot_df["ratio_Edp_percent"].to_numpy(dtype=float) * ed_total_w / total_loss_w
    return plot_df


def extend_layers_to_x_start(
    x: np.ndarray,
    layers: list[np.ndarray],
    x_start: float = 115.0,
) -> tuple[np.ndarray, list[np.ndarray]]:
    if x.size == 0 or x[0] <= x_start:
        return x, layers

    extended_x = np.insert(x, 0, x_start)
    extended_layers = [np.insert(layer, 0, layer[0]) for layer in layers]
    return extended_x, extended_layers


def plot_single_fluid(fluid_df: pd.DataFrame, outdir: Path, year_step: int) -> Path:
    fluid = str(fluid_df["fluid"].iloc[0])
    plot_df = fluid_df.sort_values("T_HS_in_K").reset_index(drop=True).copy()
    plot_df["T_HS_in_C"] = plot_df["T_HS_in_K"] - 273.15
    plot_df = build_process_columns(plot_df)

    x = plot_df["T_HS_in_C"].to_numpy(dtype=float)
    layers = [plot_df[spec["column"]].to_numpy(dtype=float) for spec in PROCESS_SPECS]
    x, layers = extend_layers_to_x_start(x, layers, x_start=X_AXIS_VISIBLE_MIN_C)

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
        FLUID_DISPLAY_NAMES.get(fluid, fluid),
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=FLUID_TITLE_FONT_SIZE,
        color="#1F1F1F",
        fontweight="bold",
    )

    fig.subplots_adjust(left=0.26, right=0.98, top=0.97, bottom=0.30)
    outpath = outdir / f"{fluid}_process_exergy_distribution_{year_step}year.png"
    fig.savefig(outpath, bbox_inches="tight")
    plt.close(fig)
    return outpath


def select_year_step_rows(df: pd.DataFrame, year_step: int) -> pd.DataFrame:
    year_values = df["year"].to_numpy(dtype=float)
    rounded_years = np.round(year_values).astype(int)
    mask_integer = np.isclose(year_values, rounded_years, atol=1e-9)
    mask_step = np.mod(rounded_years, year_step) == 0
    selected = df.loc[mask_integer & mask_step].copy()
    if selected.empty:
        raise ValueError(f"No rows matched the requested year step {year_step}.")
    return selected


def load_subfigure_label_font() -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if TIMES_NEW_ROMAN_FONT_PATH.exists():
        return ImageFont.truetype(str(TIMES_NEW_ROMAN_FONT_PATH), SUBFIGURE_LABEL_FONT_SIZE)
    return ImageFont.load_default()


def add_subfigure_label(
    image: Image.Image,
    label: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    label_height: int | None = None,
) -> Image.Image:
    bbox = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox((0, 0), label, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    if label_height is None:
        label_height = SUBFIGURE_LABEL_TOP_PADDING + text_height + SUBFIGURE_LABEL_BOTTOM_PADDING

    tile = Image.new("RGBA", (image.width, image.height + label_height), (255, 255, 255, 255))
    tile.paste(image, (0, 0))

    draw = ImageDraw.Draw(tile)
    x = (image.width - text_width) / 2 - bbox[0]
    y = image.height + SUBFIGURE_LABEL_TOP_PADDING - bbox[1]
    draw.text((x, y), label, font=font, fill=(0, 0, 0, 255))
    return tile


def create_grid_image(image_paths: list[Path], outpath: Path) -> None:
    images = [Image.open(path).convert("RGBA") for path in image_paths]
    try:
        label_font = load_subfigure_label_font()
        labels = [f"({chr(ord('a') + idx)})" for idx, _ in enumerate(images)]
        draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        label_bboxes = [draw.textbbox((0, 0), label, font=label_font) for label in labels]
        label_height = (
            SUBFIGURE_LABEL_TOP_PADDING
            + max(bbox[3] - bbox[1] for bbox in label_bboxes)
            + SUBFIGURE_LABEL_BOTTOM_PADDING
        )
        labeled_images = [
            add_subfigure_label(image, label, label_font, label_height)
            for image, label in zip(images, labels)
        ]

        first_width, first_height = labeled_images[0].size
        if any(image.size != (first_width, first_height) for image in labeled_images[1:]):
            raise ValueError("All input images must have identical pixel dimensions.")

        cols = 3
        rows = 3
        canvas = Image.new("RGBA", (cols * first_width, rows * first_height), (255, 255, 255, 255))
        for idx, image in enumerate(labeled_images):
            row = idx // cols
            col = idx % cols
            canvas.paste(image, (col * first_width, row * first_height))
        canvas.save(outpath, compress_level=0)
    finally:
        for image in images:
            image.close()


def main() -> None:
    args = parse_args()
    csv_path = Path(args.csv).resolve()
    outdir = (
        Path(args.outdir).resolve()
        if args.outdir is not None
        else SCRIPT_DIR / f"figures_process_exergy_distribution_{args.year_step}year"
    )
    outdir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(csv_path)
    required_cols = [
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
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise KeyError(f"Input CSV is missing required columns: {missing}")

    df = select_year_step_rows(df, args.year_step)

    generated_paths: list[Path] = []
    for fluid in FLUID_ORDER:
        fluid_df = df[df["fluid"].astype(str).str.upper() == fluid].copy()
        if fluid_df.empty:
            raise ValueError(f"No rows found for fluid {fluid} after applying the {args.year_step}-year step filter.")
        generated_paths.append(plot_single_fluid(fluid_df, outdir, args.year_step))

    grid_outpath = outdir / f"process_exergy_distribution_{args.year_step}year_3x3_grid.png"
    create_grid_image(generated_paths, grid_outpath)

    print(f"Input CSV: {csv_path}")
    print(f"Year step: {args.year_step}")
    print(f"Output directory: {outdir}")
    for outpath in generated_paths:
        print(f"Generated: {outpath}")
    print(f"Generated grid: {grid_outpath}")


if __name__ == "__main__":
    main()
