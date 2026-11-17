import tempfile
import unittest
from pathlib import Path

from organizer.classifier import FileClassifier
from organizer.file_organizer import FileOrganizer


class OrganizerTestCase(unittest.TestCase):
    """Shared temp-folder helpers for tests that need a folder of files."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.classifier = FileClassifier()

    def tearDown(self):
        self._tmp.cleanup()

    def make(self, relative, content="x"):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def read(self, relative):
        return (self.root / relative).read_text()

    def organizer(self, dry_run=True):
        return FileOrganizer(self.root, self.classifier, dry_run=dry_run)

    def snapshot(self):
        return sorted(p.relative_to(self.root) for p in self.root.rglob("*"))

    def rel_plan(self, plan):
        return sorted(
            (
                src.relative_to(self.root).as_posix(),
                dst.relative_to(self.root).as_posix(),
            )
            for src, dst in plan
        )
