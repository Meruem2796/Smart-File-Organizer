import shutil
import time
from pathlib import Path


class FileMover:
    def __init__(self, source, destination):
        self.source = Path(source)
        self.destination = Path(destination)
        self.status = "pending"
        self.start_time = None
        self.end_time = None
        self.error = None

    def __enter__(self):  # runs when the `with` block starts
        self.start_time = time.time()
        self.status = "running"
        return self  # this becomes `mover` in: as mover

    def execute(self):
        if self.status != "running":
            raise RuntimeError(
                "execute() must be called inside a 'with' block"
            )
        if self.source.is_dir():
            raise IsADirectoryError(
                f"Refusing to move a folder: {self.source}"
            )
        if not self.source.is_file():
            raise FileNotFoundError(f"Source file not found: {self.source}")
        if self.destination.exists() or self.destination.is_symlink():
            raise FileExistsError(
                f"Destination already exists: {self.destination}"
            )
        shutil.move(str(self.source), str(self.destination))

    def __exit__(self, exc_type, exc_value, traceback):
        self.end_time = (
            time.time()
        )  # runs when the block ends, even after an error
        if exc_type is None:
            self.status = "done"
        else:
            self.status = "failed"
            self.error = exc_value
        return False  # False = the error continues, never hidden

    @property
    def duration(self):
        if self.end_time is None:  # the move has not finished yet
            return None
        return self.end_time - self.start_time
