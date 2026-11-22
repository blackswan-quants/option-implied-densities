"""Project settings and logging setup."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    """Paths and credentials read from the environment.

    Attributes
    ----------
    data_dir : Path
        Root folder for local data. Never committed.
    api_key : str | None
        Key for the option data provider, if one is used.
    """

    data_dir: Path
    api_key: str | None

    @property
    def raw_dir(self) -> Path:
        """Folder for data exactly as downloaded."""
        return self.data_dir / "raw"

    @property
    def processed_dir(self) -> Path:
        """Folder for cleaned data produced by the pipeline."""
        return self.data_dir / "processed"

    @classmethod
    def from_env(cls, env_file: Path | None = None) -> Settings:
        """Build settings from ``.env`` and environment variables.

        Parameters
        ----------
        env_file : Path, optional
            Path to the ``.env`` file. Defaults to the one in the project root.

        Returns
        -------
        Settings
        """
        load_dotenv(env_file or PROJECT_ROOT / ".env")
        data_dir = Path(os.getenv("OID_DATA_DIR", str(PROJECT_ROOT / "data")))
        return cls(data_dir=data_dir, api_key=os.getenv("OID_DATA_API_KEY"))


def setup_logging(level: int | str = logging.INFO) -> None:
    """Configure the root logger for scripts and notebooks.

    Parameters
    ----------
    level : int or str, default logging.INFO
        Logging level.
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
