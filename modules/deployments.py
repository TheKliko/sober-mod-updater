import logging
from pathlib import Path
import time
import urllib.request
from urllib.error import HTTPError, URLError, ContentTooShortError

import requests


class Deployment:
    version: str
    fileVersion: int

    def __init__(self, version: str, fileVersion: int) -> None:
        self.version = version
        self.fileVersion = fileVersion

    def download_package(self, package: str, target: Path) -> None:
        download_url: str = f"https://setup.rbxcdn.com/{self.version}-{package}"
        target.parent.mkdir(parents=True, exist_ok=True)

        try:
            start: float = time.time()
            urllib.request.urlretrieve(download_url, target)
            end: float = time.time()
            duration: float = (end - start) * 1000
            logging.info(f"DOWNLOAD {download_url} -> SUCCESS (duration: {duration:.2f}ms)")
            return

        except HTTPError as e:
            logging.error(f"DOWNLOAD {download_url} -> {e.code} {e.reason or 'Reason unknown'}")
            input("Press ENTER to exit...")
            sys.exit(1)
        except URLError as e:
            logging.error(f"DOWNLOAD {download_url} -> {e.reason}")
            input("Press ENTER to exit...")
            sys.exit(1)
        except Exception as e:
            logging.error(f"DOWNLOAD {download_url} -> {type(e).__name__}: {e}")
            input("Press ENTER to exit...")
            sys.exit(1)


class DeployHistory:
    API: str = "https://setup.rbxcdn.com/DeployHistory.txt"

    _history: list[Deployment] | None = None
    @classmethod
    def history(cls) -> list[Deployment]:
        if cls._history is not None:
            return cls._history
        cls._set_deploy_history()
        return cls._history

    @classmethod
    def _set_deploy_history(cls) -> None:
        logging.info("Loading DeployHistory...")
        url: str = cls.API
        history: list[DeployHistory] = []

        try:
            start: float = time.time()
            response = requests.get(url, timeout=(10, 15))
            response.raise_for_status()
            end: float = time.time()
            duration: float = (end - start) * 1000
            logging.info(f"GET {url} -> {response.status_code} {response.reason or 'Reason unknown'} (duration: {duration:.2f}ms)")

        except requests.HTTPError as e:
            response = e.response
            logging.error("Failed to load DeployHistory: Request failed.)")
            logging.error(f"GET {url} -> {response.status_code} {response.reason or 'Reason unknown'}")
            input("Press ENTER to exit...")
            sys.exit(1)

        except Exception:
            logging.error("Failed to load DeployHistory: Request failed.)")
            logging.error(f"GET {url} -> {type(e).__name__}: {e}")
            input("Press ENTER to exit...")
            sys.exit(1)

        data = response.text
        for line in data.splitlines():
            try:
                split: list[str] = line.split()
                if split[1] != "Studio64" or split[7] != "file" or split[8] != "version:":
                    continue
                version = split[2]
                fileVersion = int(split[10].removesuffix(","))
                deployment: Deployment = Deployment(version, fileVersion)
                history.append(deployment)
            except Exception:
                continue
        history.reverse()
        cls._history = history

    @classmethod
    def search(cls, fileVersion: int) -> Deployment:
        history = cls.history()
        logging.info(f"Searching DeployHistory (Target version: {fileVersion})")
        for deployment in history:
            if deployment.fileVersion == fileVersion:
                return deployment
        else:
            logging.error(f"Deployment not found! (Target version: {fileVersion})")
            input("Press ENTER to exit...")
            sys.exit(1)