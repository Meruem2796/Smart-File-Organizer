import unittest

from tests.helpers import OrganizerTestCase


class TestEndToEnd(OrganizerTestCase):
    def build_messy_folder(self):
        self.make("report.pdf", "root report")
        self.make(
            "downloads/report.pdf", "downloads report"
        )  # same name, different content
        self.make("a.png", "same picture")
        self.make("trips/b.png", "same picture")  # same content as a.png
        self.make(
            "trips/Images/c.png", "nested in a folder named like a category"
        )
        self.make("song.mp3", "song")
        self.make("README", "no extension")
        self.make("empty.txt", "")
        self.make("node_modules/pkg/logo.png", "must stay")
        self.make("logs/app.log", "must stay")

    def contents(self):
        return sorted(
            p.read_bytes() for p in self.root.rglob("*") if p.is_file()
        )

    def test_scan_organize_and_find_duplicates(self):
        self.build_messy_folder()
        before = self.contents()
        layout = self.snapshot()

        # 1. a dry run changes nothing
        code, _, _ = self.run_cli("organize", str(self.root), "--dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(self.snapshot(), layout)

        # 2. the real run sorts the files and loses nothing
        code, _, _ = self.run_cli("organize", str(self.root))
        self.assertEqual(code, 0)
        self.assertEqual(
            self.contents(), before
        )  # no file lost, overwritten or copied
        self.assertEqual(
            {
                self.read("Documents/report.pdf"),
                self.read("Documents/report_1.pdf"),
            },
            {"root report", "downloads report"},
        )
        for expected in (
            "Images/a.png",
            "Images/b.png",
            "Images/c.png",
            "Audio/song.mp3",
            "Others/README",
            "Documents/empty.txt",
        ):
            self.assertTrue((self.root / expected).is_file(), expected)
        self.assertTrue(
            (self.root / "node_modules/pkg/logo.png").is_file()
        )  # skipped folders
        self.assertTrue(
            (self.root / "logs/app.log").is_file()
        )  # stay untouched

        # 3. a second run has nothing left to do
        layout = self.snapshot()
        _, out, _ = self.run_cli("organize", str(self.root))
        self.assertIn("Moved 0 file(s)", out)
        self.assertEqual(self.snapshot(), layout)

        # 4. the duplicates are still found afterwards, and nothing is deleted
        code, out, _ = self.run_cli("duplicates", str(self.root))
        self.assertEqual(code, 0)
        self.assertIn("Found 1 group(s)", out)
        self.assertNotIn("node_modules", out)  # skipped folders are not hashed
        self.assertEqual(self.contents(), before)


if __name__ == "__main__":
    unittest.main()
