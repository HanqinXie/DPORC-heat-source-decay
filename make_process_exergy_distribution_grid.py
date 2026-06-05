from __future__ import annotations

from pathlib import Path

from PIL import Image


SCRIPT_DIR = Path(__file__).resolve().parent
INPUT_DIR = SCRIPT_DIR / "figures_process_exergy_distribution"
OUTPUT_PATH = INPUT_DIR / "process_exergy_distribution_3x3_grid.png"
OUTPUT_PATH_1920 = INPUT_DIR / "process_exergy_distribution_3x3_grid_1920x1080.png"
TARGET_SIZE_1920 = (1920, 1080)

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


def image_path_for_fluid(fluid: str) -> Path:
    return INPUT_DIR / f"{fluid}_process_exergy_distribution.png"


def fit_size_within_box(src_size: tuple[int, int], dst_size: tuple[int, int]) -> tuple[int, int]:
    src_w, src_h = src_size
    dst_w, dst_h = dst_size
    scale = min(dst_w / src_w, dst_h / src_h)
    return max(1, int(round(src_w * scale))), max(1, int(round(src_h * scale)))


def main() -> None:
    image_paths = [image_path_for_fluid(fluid) for fluid in FLUID_ORDER]
    missing = [str(path) for path in image_paths if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing input images:\n" + "\n".join(missing))

    images = [Image.open(path).convert("RGBA") for path in image_paths]
    try:
        first_width, first_height = images[0].size
        if any(im.size != (first_width, first_height) for im in images[1:]):
            raise ValueError("All input images must have identical pixel dimensions.")

        cols = 3
        rows = 3
        canvas = Image.new("RGBA", (cols * first_width, rows * first_height), (255, 255, 255, 255))

        for idx, image in enumerate(images):
            row = idx // cols
            col = idx % cols
            canvas.paste(image, (col * first_width, row * first_height))

        canvas.save(OUTPUT_PATH, compress_level=0)

        fitted_size = fit_size_within_box(canvas.size, TARGET_SIZE_1920)
        resized_grid = canvas.resize(fitted_size, Image.Resampling.LANCZOS)
        canvas_1920 = Image.new("RGBA", TARGET_SIZE_1920, (255, 255, 255, 255))
        offset_x = (TARGET_SIZE_1920[0] - fitted_size[0]) // 2
        offset_y = (TARGET_SIZE_1920[1] - fitted_size[1]) // 2
        canvas_1920.paste(resized_grid, (offset_x, offset_y))
        canvas_1920.save(OUTPUT_PATH_1920, compress_level=0)
    finally:
        for image in images:
            image.close()

    print(f"Saved grid image to: {OUTPUT_PATH}")
    print(f"Grid pixel size: {cols * first_width} x {rows * first_height}")
    print(f"Saved 1920x1080 grid image to: {OUTPUT_PATH_1920}")


if __name__ == "__main__":
    main()
