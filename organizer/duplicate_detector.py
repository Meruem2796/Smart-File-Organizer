import hashlib
import logging
import stat
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)


class DuplicateDetector:
    def __init__(self, files, chunk_size=4096, include_empty=False):
        if not isinstance(chunk_size, int) or chunk_size <= 0:
            # chunk_size=0 would make every file "hash" to the same empty-input value
            raise ValueError(
                f"chunk_size must be a positive integer, got {chunk_size!r}"
            )
        self.files = list(
            dict.fromkeys(Path(f) for f in files)
        )  # drops repeated paths, keeps order
        self.chunk_size = chunk_size
        self.include_empty = include_empty
        self.groups = []
        self.skipped = []  # (path, reason) for files that could not be checked
        self._sizes = {}  # path -> size in bytes, filled by find_duplicates()

    def calculate_file_hash(self, path):
        hasher = hashlib.sha256()
        with open(path, "rb") as f:  # "rb" = read bytes
            while chunk := f.read(
                self.chunk_size
            ):  # one chunk at a time, stops at end of file
                hasher.update(chunk)
        return hasher.hexdigest()

    def _skip(self, path, reason):
        logger.warning("Skipped %s: %s", path, reason)
        self.skipped.append((path, reason))

    def _regular_file_size(self, path):
        """Return the size of a regular file, or None (and record why) if it must be skipped."""
        try:
            info = (
                path.lstat()
            )  # lstat looks at a symlink itself, not its target
        except OSError as error:  # missing file, permission denied, ...
            self._skip(path, error)
            return None
        if not stat.S_ISREG(info.st_mode):  # folders, symlinks, pipes, devices
            self._skip(path, "not a regular file")
            return None
        return info.st_size

    def find_duplicates(self):
        self.groups = []
        self.skipped = []
        self._sizes = {}

        by_size = defaultdict(list)
        for path in self.files:
            size = self._regular_file_size(path)
            if size is None:
                continue
            if size == 0 and not self.include_empty:
                continue  # empty files are all "identical": just noise
            self._sizes[path] = size
            by_size[size].append(path)

        for same_size in by_size.values():
            if len(same_size) < 2:
                continue  # a unique size cannot have a duplicate
            by_hash = defaultdict(list)
            for path in same_size:
                try:
                    by_hash[self.calculate_file_hash(path)].append(path)
                except OSError as error:  # locked, deleted meanwhile, ...
                    self._skip(path, error)
            self.groups.extend(
                sorted(g) for g in by_hash.values() if len(g) > 1
            )

        self.groups.sort()  # stable, readable output
        return self.groups

    def generate_duplicate_report(self):
        lines = []
        if not self.groups:
            lines.append("No duplicates found.")
        else:
            reclaimable = 0
            for number, group in enumerate(self.groups, start=1):
                size = self._sizes[group[0]]
                reclaimable += size * (
                    len(group) - 1
                )  # keep one copy, the rest is extra
                lines.append(
                    f"Group {number}: {len(group)} files, {self._format_size(size)} each"
                )
                lines.extend(f"  {path}" for path in group)
            lines.append(
                f"Found {len(self.groups)} group(s) of duplicates; "
                f"{self._format_size(reclaimable)} could be reclaimed. Nothing was deleted."
            )
        if self.skipped:
            lines.append(
                f"Skipped {len(self.skipped)} file(s) that could not be checked."
            )
        return "\n".join(lines)

    @staticmethod
    def _format_size(size):
        if size < 1024:
            return f"{size} bytes"
        for unit in ("KB", "MB", "GB"):
            size /= 1024
            if size < 1024 or unit == "GB":
                return f"{size:.1f} {unit}"
