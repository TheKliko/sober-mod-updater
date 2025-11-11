import hashlib
import json
import logging
import os
from pathlib import Path
import re
import shutil
import sys
from tempfile import TemporaryDirectory

try:
    from modules.deployments import DeployHistory, Deployment
    from modules.mod import Mod
    from modules.imagesets import Icon, ImageSet, get_imagesetdata
    from modules import zip_extractor

    from PIL import Image
except (ImportError, ModuleNotFoundError) as e:
    input(e)
    sys.exit(1)


class Config:
    PATH = Path("config.json").resolve()

    target_version: int
    mod_path: Path

    def __init__(self) -> None:
        if not self.PATH.exists():
            logging.error(f"Failed to load config: Config not found! ({self.PATH})")
            input("Press ENTER to exit...")
            sys.exit(1)

        with open(self.PATH, "r") as file:
            data = json.load(file)
        target_version = data.get("target_version")
        mod_path = data.get("mod_path")

        try:
            if target_version is None:
                logging.warning("Failed to load config[target_version]: target_version is None")
                print()
                target_version = input("Target version: ")
            target_version = int(target_version)
            self.target_version = target_version
        except ValueError as e:
            logging.error(f"Failed to load config[target_version]: {e}")
            input("Press ENTER to exit...")
            sys.exit(1)

        if mod_path is None:
                logging.warning("Failed to load config[mod_path]: mod_path is None")
                print()
                mod_path = input("Mod path: ")
        if isinstance(mod_path, str):
            mod_path = Path(mod_path).expanduser().resolve()
        elif isinstance(mod_path, list) and all(isinstance(item, str) for item in mod_path):
            mod_path = Path(*mod_path).expanduser().resolve()
        else:
            logging.error(f"Failed to load config[mod_path]: TypeError: mod_path must be of type 'str' or 'list[str]', not '{type(mod_path)}'")
            input("Press ENTER to exit...")
            sys.exit(1)
        if not mod_path.exists():
            logging.error("Failed to load config[mod_path]: Path does not exist!")
            input("Press ENTER to exit...")
            sys.exit(1)
        self.mod_path = mod_path


# https://stackoverflow.com/a/44873382
def sha256sum(target: Path) -> str:
    h  = hashlib.sha256()
    b  = bytearray(128*1024)
    mv = memoryview(b)
    with open(target, 'rb', buffering=0) as f:
        while n := f.readinto(mv):
            h.update(mv[:n])
    return h.hexdigest()


def compare_images(image1: Image.Image, image2: Image.Image) -> bool:
    if image1.size != image2.size:
        return False
    
    image1_data = image1.getdata()
    image2_data = image2.getdata()

    for pixel1, pixel2 in zip(image1_data, image2_data):
        a1, a2 = pixel1[3], pixel2[3]
        if a1 != a2:
            return False
        elif a1 == 0:
            continue
        elif pixel1[:3] != pixel2[:3]:
            return False
    return True


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)-8s] | %(message)s"
    )

    logging.info("Loading config...")
    config = Config()

    logging.info("Loading mod info...")
    mod = Mod(config.mod_path)

    if mod.fileVersion == config.target_version:
        logging.warning("Mod version and target version are the same!")
        input("Press ENTER to exit...")
        sys.exit(0)

    with TemporaryDirectory(prefix="sober-mod-updater-") as tmp:
        temp_dir = Path(tmp).resolve()
        logging.info(f"Temporary directory: {temp_dir}")
        mod_imagesets = mod.luapackages / mod.image_set_directory
        mod_imagesets_copy = temp_dir / "mod_imagesets"
        logging.info("Copying mod imageSets...")
        shutil.copytree(mod_imagesets, mod_imagesets_copy)

        # Getting deployment info
        mod_deployment: Deployment = DeployHistory.search(mod.fileVersion)
        target_deployment: Deployment = DeployHistory.search(config.target_version)

        logging.info("Downloading LuaPackages...")
        package: str = "extracontent-luapackages.zip"
        download_dir: Path = temp_dir / "download"
        mod_deployment.download_package(package, download_dir / "mod_luapackages.zip")
        target_deployment.download_package(package, download_dir / "target_luapackages.zip")

        mod_luapackages: Path = temp_dir / "mod_luapackages"
        target_luapackages: Path = temp_dir / "target_luapackages"

        logging.info("Extracting LuaPackages...")
        zip_extractor.extract(download_dir / "mod_luapackages.zip", mod_luapackages)
        zip_extractor.extract(download_dir / "target_luapackages.zip", target_luapackages)

        pattern = re.compile(r"^img_set_[1-3]x_\d+\.png$")
        for (root, dirs, files) in os.walk(target_luapackages):
            if any(pattern.match(file) for file in files):
                target_image_set_directory = Path(root).relative_to(target_luapackages)
                break
        else:
            logging.error(f"Unable to update mod: imageSets not found in target version ({config.target_version})")
            input("Press ENTER to exit...")
            sys.exit(1)

        logging.info("Checking for GetImageSetData.lua")
        mod_imagesetdata_file: Path = (mod_luapackages / mod.image_set_directory).parent / "Generated" / "GetImageSetData.lua"
        target_imagesetdata_file: Path = (target_luapackages / target_image_set_directory).parent / "Generated" / "GetImageSetData.lua"

        if not mod_imagesetdata_file.exists():
            logging.error(f"Unable to update mod: GetImageSetData.lua not found in mod version ({mod.fileVersion})")
            input("Press ENTER to exit...")
            sys.exit(1)
        if not target_imagesetdata_file.exists():
            logging.error(f"Unable to update mod: GetImageSetData.lua not found in target version ({config.target_version})")
            input("Press ENTER to exit...")
            sys.exit(1)
        
        logging.info("Comparing file hashes...")
        if sha256sum(mod_imagesetdata_file) == sha256sum(target_imagesetdata_file):
            logging.warning(f"Unable to update mod: Mod is not outdated!")
            mod.update_info(config.target_version)
            input("Press ENTER to exit...")
            sys.exit(1)

        logging.info("Parsing data...")
        mod_imagesetdata: list[ImageSet] = get_imagesetdata(mod_imagesetdata_file, mod_luapackages / mod.image_set_directory)
        target_imagesetdata: list[ImageSet] = get_imagesetdata(target_imagesetdata_file, target_luapackages / target_image_set_directory)

        logging.info("Detecting modded icons...")
        modded_icon_count: int = 0
        modded_icon_data: dict[str, dict[str, tuple[tuple[int, int, int, int], Image.Image]]] = {}
        for imageset in mod_imagesetdata:
            mod_imageset_path: Path = mod_imagesets_copy / f"{imageset.name}.png"
            if not mod_imageset_path.exists():
                logging.info(f"Skipping '{imageset.name}': File not found!")
                continue

            with Image.open(imageset.path) as original_image:
                if original_image.mode != "RGBA":
                    original_image = original_image.convert("RGBA")

                with Image.open(mod_imageset_path) as mod_image:
                    if mod_image.mode != "RGBA":
                        mod_image = mod_image.convert("RGBA")

                    for icon in imageset.icons:
                        original_icon: Image.Image = original_image.crop(icon.box)
                        mod_icon: Image.Image = mod_image.crop(icon.box)
                        if compare_images(mod_icon, original_icon):
                            continue  # Image is not modded

                        if imageset.size not in modded_icon_data:
                            modded_icon_data[imageset.size] = {}
                        modded_icon_data[imageset.size][icon.name] = (icon.box, mod_icon)
                        modded_icon_count += 1

        if modded_icon_count == 0:
            logging.warning(f"Unable to update mod: No modded icons detected!")
            mod.update_info(config.target_version)
            input("Press ENTER to exit...")
            sys.exit(1)

        logging.info(f"{modded_icon_count} modded icons detected")

        logging.info("Detecting new icon positions...")
        updated_icon_data: dict[str, list[tuple[tuple[int, int, int, int], Image.Image]]] = {}
        for imageset in target_imagesetdata:
            modded_icons: dict[str, tuple] | None = modded_icon_data.get(imageset.size)
            if modded_icons is None:
                continue
            for icon in imageset.icons:
                modded_icon: tuple | None = modded_icons.get(icon.name)
                if modded_icon is None:
                    continue
                if imageset.name not in updated_icon_data:
                    updated_icon_data[imageset.name] = []
                updated_icon_data[imageset.name].append((icon.box, modded_icon[1]))
        
        if not updated_icon_data:
            logging.error("Failed to update mod: modded icons not found in new imageSets!")
            input("Press ENTER to exit...")
            sys.exit(1)

        logging.info("Updating new imageSets...")
        removed_imageset_count: int = 0
        for imageset in target_imagesetdata:
            modded_icons: list[tuple[tuple[int, int, int, int], Image.Image]] | None = updated_icon_data.get(imageset.name)
            if modded_icons is None:  # Remove unmodded imageSets
                # logging.warning(f"Removing unmodded imageSet: '{imageset.name}'")
                removed_imageset_count += 1
                imageset.path.unlink()
                continue

            with Image.open(imageset.path) as new_image:
                if new_image.mode != "RGBA":
                    new_image = new_image.convert("RGBA")

                for box, icon in modded_icons:
                    new_image.paste(icon, box)
                
                new_image.save(imageset.path, format="PNG")
        
        logging.info("Done!")
        logging.warning(f"Removed {removed_imageset_count} unmodded imageSets")

        mod.backup()
        mod.update(target_luapackages / target_image_set_directory, target_image_set_directory, config.target_version)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print()
        print("[FATAL] Uncaught Exception!")
        print(type(e), e)
        input("Press ENTER to exit...")
        sys.exit(1)
    else:
        input("Press ENTER to exit...")