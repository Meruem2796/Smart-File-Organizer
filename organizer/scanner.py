import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_EXCLUDED_DIRECTORIES = (
    "AppData",
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "logs",
    "log",
)


class FileScanner:
    def __init__(self, directory, recursive=False, excluded_directories=()):
        self.directory = Path(directory)
        self.recursive = recursive
        self.excluded_directories = {
            name.casefold() for name in excluded_directories
        }
        self.files = []

    def scan_directory(self):
        if not self.directory.is_dir():
            raise NotADirectoryError(f"Not a directory: {self.directory}")

        pattern = "**/*" if self.recursive else "*"
        self.files = []
        for path in self.directory.glob(pattern):
            if path.is_symlink():
                continue  # never follow links out of the folder
            # [:-1] drops the file name: only parent FOLDERS can exclude a path
            parent_parts = path.relative_to(self.directory).parts[:-1]
            if any(
                part.casefold() in self.excluded_directories
                for part in parent_parts
            ):
                continue
            if path.is_file():
                self.files.append(path)
        return self.files

    def iter_files(self):
        for path in self.files:
            yield path

    def get_file_metadata(self, path):
        try:
            info = path.stat()
        except (FileNotFoundError, PermissionError) as error:
            logger.warning("Cannot read metadata for %s: %s", path, error)
            return None  # caller must check for None
        return {
            "name": path.name,
            "size": info.st_size,
            "extension": path.suffix.lower(),
            "modified": datetime.fromtimestamp(info.st_mtime),
        }
