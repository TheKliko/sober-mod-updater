import json
import logging
import os
from pathlib import Path
import re
import shutil
import sys


class Mod:
    name: str
    path: Path
    luapackages: Path
    image_set_directory: Path
    fileVersion: int
    _backup: Path | None = None

    def __init__(self, path: Path) -> None:
        self.path = path
        self.name = path.name

        info_path: Path = self.path / "info.json"
        if not info_path.exists():
            logging.error("Failed to load mod info: info.json file does not exist!")
            input("Press ENTER to exit...")
            sys.exit(1)
        
        with open(info_path, "r") as file:
            data = json.load(file)
        fileVersion = data.get("fileVersion")
        try:
            if fileVersion is None:
                logging.warning("Failed to load mod info[fileVersion]: fileVersion is None")
                print()
                fileVersion = input("Mod file version: ")
            fileVersion = int(fileVersion)
            self.fileVersion = fileVersion
        except ValueError as e:
            logging.error(f"Failed to load mod info[fileVersion]: {e}")
            input("Press ENTER to exit...")
            sys.exit(1)
        
        logging.info("Locating imageSets...")
        self.luapackages: Path = self.path / "ExtraContent" / "LuaPackages"
        if not self.luapackages.exists():
            logging.error("Incompatible mod: LuaPackages does not exist!")
            input("Press ENTER to exit...")
            sys.exit(1)
        pattern = re.compile(r"^img_set_[1-3]x_\d+\.png$")
        for (root, dirs, files) in os.walk(self.luapackages):
            if any(pattern.match(file) for file in files):
                self.image_set_directory = Path(root).relative_to(self.luapackages)
                break
        else:
            logging.error("Incompatible mod: imageSets not found!")
            input("Press ENTER to exit...")
            sys.exit(1)
        logging.info(self.image_set_directory)

    def backup(self) -> None:
        logging.info(f"Backing up mod: {self.name}")
        target: Path = self.path.with_name(f"{self.name}.mod-updater-backup")
        if target.exists():
            logging.warning("Removing existing backup...")
            shutil.rmtree(target)
            logging.info("Backing up mod...")
        shutil.copytree(self.path, target)
        logging.info("Backup complete!")

    def restore_backup(self) -> None:
        if self._backup is None:
            logging.error("Failed to restore backup: No backup was made!")
            input("Press ENTER to exit...")
            sys.exit(1)

        if self.path.exists():
            logging.error("Failed to restore backup: Original mod exists!")
            print(f"Please restore the backup manually: {self._backup}")

        logging.info(f"Restoring backup: {self._backup.name}")
        self._backup.rename(self.path)
        logging.info("Backup restored!")
        logging.info("Removing backup...")
        shutil.rmtree(self._backup)
        self._backup = None

    def update_info(self, fileVersion: int) -> None:
        logging.info("Updating mod info...")
        info_path: Path = self.path / "info.json"
        with open(info_path, "w") as file:
            json.dump({"fileVersion": fileVersion}, file, indent=4)
        self.fileVersion = fileVersion

    def update(self, updated_imagesets: Path, updated_imageset_directory: Path, fileVersion: int) -> None:
        logging.info(f"Updating mod files: {self.name}")

        logging.info("Removing old imageSets...")
        old_imagesets: Path = self.luapackages / self.image_set_directory
        shutil.rmtree(old_imagesets)

        parent = old_imagesets.parent
        safeguard: str = self.luapackages.name
        while not os.listdir(parent):
            if parent.name == safeguard:
                break
            parent.rmdir()
            parent = parent.parent

        logging.info("Copying new imageSets...")
        new_imagesets: Path = self.luapackages / updated_imageset_directory
        new_imagesets.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(updated_imagesets, new_imagesets)
        self.image_set_directory = updated_imageset_directory
        
        self.update_info(fileVersion)

        logging.info("Mod updated successfully!")