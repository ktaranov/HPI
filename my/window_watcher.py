"""
Parses history from https://github.com/seanbreckenridge/aw-watcher-window
"""

# see https://github.com/seanbreckenridge/dotfiles/blob/master/.config/my/my/config/__init__.py for an example
from my.config import window_watcher as user_config  # type: ignore

from dataclasses import dataclass
from typing import Optional

from .core import PathIsh, Paths


@dataclass
class window_watcher(user_config):
    # path[s]/glob to the backed up window_watcher history files
    export_path: Paths

    # path to current window_watcher history (i.e. the live file)
    live_file: Optional[PathIsh] = None


from .core.cfg import make_config

config = make_config(window_watcher)

#######

import csv
import warnings
from pathlib import Path
from typing import Sequence

from .core import get_files, warn_if_empty
from .core.common import listify


@listify
def inputs() -> Sequence[Path]:  # type: ignore
    """
    Returns all inputs, including live_file if provided and backups
    """
    yield from get_files(config.export_path)
    if config.live_file is not None:
        p: Path = Path(config.live_file).expanduser().absolute()
        if p.exists():
            yield p
        else:
            warnings.warn(
                f"'live_file' provided {config.live_file} but that file doesn't exist."
            )


from datetime import datetime, timezone
from typing import NamedTuple, Iterable, Set
from itertools import chain


# represents one history entry (command)
class Entry(NamedTuple):
    dt: datetime
    duration: int
    application: str
    window_title: str


Results = Iterable[Entry]


def history(from_paths=inputs) -> Results:
    yield from _merge_histories(*map(_parse_file, from_paths()))


@warn_if_empty
def _merge_histories(*sources: Results) -> Results:
    emitted: Set[datetime] = set()
    for e in chain(*sources):
        key = e.dt
        if key in emitted:
            # print('ignoring %s: %s', key, e)
            continue
        yield e
        emitted.add(key)


def _parse_file(histfile: Path) -> Results:
    with open(histfile, "r") as f:
        csv_reader = csv.reader(f, delimiter=",")
        for row in csv_reader:
            yield Entry(
                dt=datetime.fromtimestamp(int(row[0]), tz=timezone.utc),
                duration=int(row[1]),
                application=row[2],
                window_title=row[3],
            )


def stats():
    from .core import stat

    return {**stat(history)}