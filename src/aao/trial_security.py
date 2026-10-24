"""Small filesystem guards shared by the root trial runner and tests."""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path


def validate_role_workdir(path: str | os.PathLike[str], uid: int) -> bool:
    """Return true only for a real directory owned by uid with exact mode 0700."""
    try:
        info = Path(path).lstat()
    except OSError:
        return False
    return stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode) and info.st_uid == uid and stat.S_IMODE(info.st_mode) == 0o700


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(2)
    raise SystemExit(0 if validate_role_workdir(sys.argv[1], int(sys.argv[2])) else 1)
