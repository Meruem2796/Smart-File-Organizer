import tempfile
import unittest
from pathlib import Path

from organizer.file_mover import FileMover


class TestFileMover(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.source = self.root / "report.pdf"
        self.source.write_text("data")
        (self.root / "Documents").mkdir()
        self.destination = self.root / "Documents" / "report.pdf"

    def tearDown(self):
        self._tmp.cleanup()

    def test_successful_move(self):
        with FileMover(self.source, self.destination) as mover:
            self.assertEqual(mover.status, "running")
            mover.execute()
        self.assertEqual(mover.status, "done")
        self.assertIsNone(mover.error)
        self.assertGreaterEqual(mover.end_time, mover.start_time)
        self.assertGreaterEqual(mover.duration, 0)
        self.assertFalse(self.source.exists())
        self.assertEqual(self.destination.read_text(), "data")

    def test_duration_is_none_before_exit(self):
        mover = FileMover(self.source, self.destination)
        self.assertEqual(mover.status, "pending")
        self.assertIsNone(mover.duration)
        with mover:
            self.assertIsNone(mover.duration)

    def test_never_overwrites_existing_destination(self):
        self.destination.write_text("old")
        with self.assertRaises(FileExistsError):
            with FileMover(self.source, self.destination) as mover:
                mover.execute()
        self.assertEqual(mover.status, "failed")
        self.assertIsInstance(mover.error, FileExistsError)
        self.assertEqual(self.destination.read_text(), "old")
        self.assertEqual(self.source.read_text(), "data")

    def test_missing_source_fails(self):
        self.source.unlink()
        with self.assertRaises(FileNotFoundError):
            with FileMover(self.source, self.destination) as mover:
                mover.execute()
        self.assertEqual(mover.status, "failed")

    def test_folder_is_not_moved(self):
        folder = self.root / "sub"
        folder.mkdir()
        with self.assertRaises(IsADirectoryError):
            with FileMover(folder, self.root / "Documents" / "sub") as mover:
                mover.execute()
        self.assertTrue(folder.is_dir())

    def test_execute_outside_with_block_is_refused(self):
        mover = FileMover(self.source, self.destination)
        with self.assertRaises(RuntimeError):
            mover.execute()
        self.assertTrue(self.source.exists())

    def test_exit_does_not_hide_exceptions(self):
        with self.assertRaises(ZeroDivisionError):
            with FileMover(self.source, self.destination) as mover:
                1 / 0
        self.assertEqual(mover.status, "failed")
        self.assertIsInstance(mover.error, ZeroDivisionError)
        self.assertIsNotNone(
            mover.duration
        )  # timing is recorded even on failure


if __name__ == "__main__":
    unittest.main()
