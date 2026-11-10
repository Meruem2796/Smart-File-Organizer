import tempfile
import unittest
from pathlib import Path

from organizer.scanner import FileScanner


class TestFileScanner(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "a.txt").write_text("a")
        (self.root / "b.PNG").write_text("bb")
        (self.root / "sub").mkdir()
        (self.root / "sub" / "c.py").write_text("ccc")
        (self.root / "skipme").mkdir()
        (self.root / "skipme" / "d.txt").write_text("d")

    def tearDown(self):
        self._tmp.cleanup()

    def test_non_recursive_finds_only_top_level_files(self):
        files = FileScanner(self.root).scan_directory()
        self.assertEqual({p.name for p in files}, {"a.txt", "b.PNG"})

    def test_recursive_finds_nested_files(self):
        files = FileScanner(self.root, recursive=True).scan_directory()
        self.assertEqual(
            {p.name for p in files}, {"a.txt", "b.PNG", "c.py", "d.txt"}
        )

    def test_never_returns_folders(self):
        files = FileScanner(self.root, recursive=True).scan_directory()
        self.assertTrue(all(p.is_file() for p in files))

    def test_excluded_directories_are_skipped(self):
        scanner = FileScanner(
            self.root, recursive=True, excluded_directories=["skipme"]
        )
        names = {p.name for p in scanner.scan_directory()}
        self.assertNotIn("d.txt", names)

    def test_iter_files_is_a_generator_over_self_files(self):
        scanner = FileScanner(self.root)
        scanner.scan_directory()
        gen = scanner.iter_files()
        self.assertEqual(next(gen), scanner.files[0])  # one at a time
        self.assertEqual(len(list(gen)), len(scanner.files) - 1)

    def test_metadata_fields(self):
        scanner = FileScanner(self.root)
        meta = scanner.get_file_metadata(self.root / "b.PNG")
        self.assertEqual(meta["name"], "b.PNG")
        self.assertEqual(meta["size"], 2)
        self.assertEqual(meta["extension"], ".png")  # lowercased

    def test_metadata_for_missing_file_returns_none(self):
        scanner = FileScanner(self.root)
        self.assertIsNone(scanner.get_file_metadata(self.root / "nope.txt"))

    def test_missing_directory_raises(self):
        with self.assertRaises(NotADirectoryError):
            FileScanner(self.root / "does_not_exist").scan_directory()


if __name__ == "__main__":
    unittest.main()
