"""Entry point: checks the data file every few seconds."""

import signal
import sys
import time

from settings import Settings
from watcher import Watcher


def main() -> None:
    settings = Settings.from_env()
    watcher = Watcher(settings)

    # As PID 1 in a container, Python ignores SIGTERM unless told otherwise.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

    while True:
        watcher.check()
        time.sleep(settings.interval)


if __name__ == "__main__":
    main()
