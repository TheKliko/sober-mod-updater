from pathlib import Path
from zipfile import ZipFile


def extract(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)

    with ZipFile(source, "r") as archive:
        for member in archive.namelist():
            normalized = member.lstrip("\\/").replace("\\\\", "/").replace("\\", "/")
            if not normalized.strip():
                continue
            target: Path = destination / normalized
            if normalized.endswith("/"):
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as archived, open(target, "wb") as file:
                    file.write(archived.read())