import tempfile
import unittest
from pathlib import Path

from organizer.classifier import FileClassifier
from organizer.file_organizer import FileOrganizer


class TestFileOrganizerDryRun(unittest.TestCase):
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

    def test_preview_plans_category_destinations(self):
        self.make("photo.png")
        self.make("notes.txt")
        plan = self.rel_plan(self.organizer().preview_organization())
        self.assertEqual(
            plan,
            [
                ("notes.txt", "Documents/notes.txt"),
                ("photo.png", "Images/photo.png"),
            ],
        )

    def test_preview_touches_nothing(self):
        self.make("photo.png")
        self.make("sub/notes.txt")
        before = self.snapshot()
        self.organizer().preview_organization()
        self.assertEqual(self.snapshot(), before)

    def test_dry_run_organize_directory_changes_nothing_and_summarizes(self):
        self.make("a.png")
        self.make("b.png")
        self.make("c.txt")
        before = self.snapshot()
        summary = self.organizer().organize_directory()
        self.assertEqual(summary, {"Images": 2, "Documents": 1})
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.root / "Images").exists())  # no folders created

    def test_files_in_top_level_category_folders_are_ignored(self):
        self.make("Images/old.png")
        self.make("images/lower.png")  # case-insensitive match
        self.assertEqual(self.organizer().preview_organization(), [])

    def test_nested_folder_named_like_a_category_is_still_organized(self):
        self.make("trips/Images/a.png")
        plan = self.rel_plan(self.organizer().preview_organization())
        self.assertEqual(plan, [("trips/Images/a.png", "Images/a.png")])

    def test_root_file_named_like_a_category_is_not_ignored(self):
        self.make("Code")  # no extension -> "Others"
        plan = self.rel_plan(self.organizer().preview_organization())
        self.assertEqual(plan, [("Code", "Others/Code")])

    def test_same_name_files_get_distinct_planned_destinations(self):
        self.make("a/report.pdf")
        self.make("b/report.pdf")
        destinations = {
            dst.name for _, dst in self.organizer().preview_organization()
        }
        self.assertEqual(destinations, {"report.pdf", "report_1.pdf"})

    def test_existing_file_in_category_folder_forces_suffix(self):
        self.make("Documents/report.pdf")
        self.make("report.pdf")
        plan = self.organizer().preview_organization()
        self.assertEqual([dst.name for _, dst in plan], ["report_1.pdf"])

    def test_organize_file_dry_run_never_reuses_a_planned_name(self):
        first = self.make("a/report.pdf")
        second = self.make("b/report.pdf")
        organizer = self.organizer()
        self.assertEqual(organizer.organize_file(first).name, "report.pdf")
        self.assertEqual(organizer.organize_file(second).name, "report_1.pdf")

    def test_preview_matches_dry_run_organize(self):
        self.make("a/report.pdf")
        self.make("b/report.pdf")
        organizer = self.organizer()
        planned = [dst for _, dst in organizer.preview_organization()]
        organizer._planned = set()
        via_organize = [
            organizer.organize_file(src)
            for src, _ in organizer.preview_organization()
        ]
        self.assertEqual(planned, via_organize)

    def test_custom_category_is_respected(self):
        self.classifier.register_category("Logs")(lambda p: p.suffix == ".log")
        self.make("app.log")
        plan = self.rel_plan(self.organizer().preview_organization())
        self.assertEqual(plan, [("app.log", "Logs/app.log")])

    def test_refuses_missing_directory(self):
        with self.assertRaises(NotADirectoryError):
            FileOrganizer(self.root / "nope", self.classifier)

    def test_refuses_drive_root(self):
        with self.assertRaises(ValueError):
            FileOrganizer(Path(self.root.anchor), self.classifier)

    def test_refuses_home_folder(self):
        with self.assertRaises(ValueError):
            FileOrganizer(Path.home(), self.classifier)


if __name__ == "__main__":
    unittest.main()
