from dataclasses import dataclass
from pathlib import Path
import re


@dataclass
class Icon:
    name: str
    imageset: str
    x: int
    y: int
    w: int
    h: int
    box: tuple[int, int, int, int]


@dataclass
class ImageSet:
    name: str
    path: Path
    size: str
    icons: list[Icon]


def get_imagesetdata(data_file: Path, imageset_directory: Path) -> list[ImageSet]:
    with open(data_file, "r") as file:
        content: str = file.read()
    parsed: dict[str, dict[str, dict[str, str | int]]] = _parse_file_content(content)

    imagesets_dict: dict[str, ImageSet] = {}

    for size, icons in parsed.items():
        for name, data in icons.items():
            imageset: str = data["image_set"]
            x: int = data["x"]
            y: int = data["y"]
            w: int = data["w"]
            h: int = data["h"]
            icon: Icon = Icon(name, imageset, x, y, w, h, (x, y, x + w, y + h))

            imageset_item: ImageSet | None = imagesets_dict.get(imageset)
            if imageset_item is None:
                imagesets_dict[imageset] = ImageSet(imageset, imageset_directory / f"{imageset}.png", size, [icon])
            else:
                imageset_item.icons.append(icon)

    imagesets: list[ImageSet] = list(imagesets_dict.values())
    return imagesets


def _parse_file_content(content: str) -> dict[str, dict[str, dict[str, str | int]]]:  # ChatGPT
    icon_map: dict[str, dict[str, dict[str, str | int]]] = {}

    image_size_pattern: str = r"function make_assets_(\dx)\(\).*?(\{.*?\}) end"
    icon_data_pattern: str = r"\['([^']+)'\] = \{ ImageRectOffset = Vector2\.new\((\d+), (\d+)\), ImageRectSize = Vector2\.new\((\d+), (\d+)\), ImageSet = '([^']+)' \}"

    image_size_matches: list = re.findall(image_size_pattern, content, re.DOTALL)
    for size, data in image_size_matches:
        if size not in icon_map:
            icon_map[size] = {}

        icon_data_matches: list = re.findall(icon_data_pattern, data)
        for icon in icon_data_matches:
            name, x, y, w, h, image_set = icon
            icon_map[size][name] = {
                "image_set": image_set,
                "x": int(x),
                "y": int(y),
                "w": int(w),
                "h": int(h)
            }

    return icon_map