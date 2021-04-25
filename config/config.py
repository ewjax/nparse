import os
from dataclasses import dataclass, field
import json
import glob
from typing import List

from utils import logger

log = logger.get_logger(__name__)


@dataclass
class Config:

    eq_dir: str = ""
    update_check: bool = True
    last_profile: str = ""
    qt_scale_factor: int = 100
    use_secondary: List[str] = field(
        default_factory=lambda: ["levitate", "malise", "malisement"]
    )

    def __post_init__(self):
        try:
            self.__dict__.update(
                json.loads(open("data/nparse.config.json", "r").read()).items()
            )
        except:
            log.warning("Unable to load data/nparse.config.json", exc_info=True)

    def save(self):
        try:
            open("data/nparse.config.json", "w").write(
                json.dumps(self.__dict__, indent=4)
            )
        except:
            log.warning("Unable to save data/nparse.config.json", exc_info=True)

    def verify_paths(self):
        # verify Everquest Directory Exists (try some common paths)
        for dir in (self.eq_dir,
                    os.path.join("c:\\", "everquest"),
                    os.path.join("c:\\", "program files", "everquest"),
                    os.path.join("c:\\", "program files (x86)", "everquest"),
                    os.path.join("d:\\", "everquest"),
                    os.path.join("d:\\", "program files", "everquest"),
                    os.path.join("d:\\", "program files (x86)", "everquest")):
            # verify eq log directory contains log files for reading.
            log_filter = os.path.join(dir, "Logs", "eqlog*.*")
            if glob.glob(log_filter):
                # Found path, set and return
                self.eq_dir = dir
                return
            else:
                # Check if they selected the Log directory (old style config)
                path_parts = os.path.split(dir)
                if path_parts[-1].lower() == 'logs':
                    log_filter = os.path.join(dir, "eqlog*.*")
                    if glob.glob(log_filter):
                        self.eq_dir = os.path.join(*path_parts[:-1])
                        return

            if os.path.isdir(os.path.join(dir)):
                # Directory exists, but no logs are in it
                raise ValueError(
                    "No Logs Found",
                    (
                        "No Everquest log files were found.  Ensure both your directory is set "
                        "and logging is turned on in your Everquest client."
                    ),
                )
        raise ValueError(
            "Everquest Directory Error",
            (
                "Everquest directory needs to be set before proceeding. "
                "Use Settings->General->Everquest Directory to set it."
            ),
        )
