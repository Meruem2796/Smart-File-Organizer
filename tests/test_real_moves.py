import unittest
from unittest import mock

from organizer.file_mover import FileMover
from organizer.file_organizer import FileOrganizer
from tests.helpers import OrganizerTestCase


class TestFileOrganizerRealMoves(OrganizerTestCase):
    def test_moves_files_and_returns_summary(self):
        self.make("photo.png", "img")
        self.make("a.txt", "one")
        self.make("b.txt", "two")
        summary = self.organizer(dry_run=False).organize_directory()
        self.assertEqual(summary, {"Images": 1, "Documents": 2})
        self.assertEqual(self.read("Images/photo.png"), "img")
        self.assertEqual(self.read("Documents/a.txt"), "one")
        self.assertFalse((self.root / "photo.png").exists())

    def test_only_needed_category_folders_are_created(self):
        self.make("photo.png")
        self.organizer(dry_run=False).organize_directory()
        self.assertTrue((self.root / "Images").is_dir())
        self.assertFalse((self.root / "Audio").exists())

    def test_existing_file_is_never_overwritten(self):
        self.make("Documents/report.pdf", "old")
        self.make("report.pdf", "new")
        self.organizer(dry_run=False).organize_directory()
        self.assertEqual(self.read("Documents/report.pdf"), "old")
        self.assertEqual(self.read("Documents/report_1.pdf"), "new")

    def test_same_name_files_from_different_folders_both_survive(self):
        self.make("a/report.pdf", "A")
        self.make("b/report.pdf", "B")
        self.organizer(dry_run=False).organize_directory()
        contents = {
            self.read("Documents/report.pdf"),
            self.read("Documents/report_1.pdf"),
        }
        self.assertEqual(contents, {"A", "B"})

    def test_second_run_changes_nothing(self):
        self.make("a.png")
        self.make("sub/b.txt")
        organizer = self.organizer(dry_run=False)
        organizer.organize_directory()
        after_first_run = self.snapshot()
        summary = organizer.organize_directory()
        self.assertEqual(summary, {})
        self.assertEqual(self.snapshot(), after_first_run)

    def test_nested_file_moved_and_folders_left_in_place(self):
        self.make("sub/deep/c.mp3", "song")
        self.organizer(dry_run=False).organize_directory()
        self.assertEqual(self.read("Audio/c.mp3"), "song")
        self.assertTrue(
            (self.root / "sub" / "deep").is_dir()
        )  # nothing is ever deleted

    def test_real_run_follows_the_preview(self):
        self.make("a.png")
        self.make("b.txt")
        self.make("sub/c.mp3")
        organizer = self.organizer(dry_run=False)
        plan = organizer.preview_organization()
        organizer.organize_directory()
        for source, destination in plan:
            self.assertFalse(source.exists())
            self.assertTrue(destination.exists())

    def test_failure_is_reported_and_does_not_stop_the_run(self):
        self.make("bad.png", "keep me")
        self.make("good.txt", "moved")
        real_execute = FileMover.execute

        def flaky(mover):  # fails for one file, works for the rest
            if mover.source.name == "bad.png":
                raise PermissionError("file is locked")
            return real_execute(mover)

        organizer = self.organizer(dry_run=False)
        with mock.patch.object(FileMover, "execute", flaky):
            summary = organizer.organize_directory()

        self.assertEqual(summary, {"Documents": 1})
        self.assertEqual(len(organizer.failures), 1)
        failed_path, error = organizer.failures[0]
        self.assertEqual(failed_path.name, "bad.png")
        self.assertIsInstance(error, PermissionError)
        self.assertEqual(self.read("bad.png"), "keep me")  # untouched
        self.assertEqual(self.read("Documents/good.txt"), "moved")

    def test_mover_is_a_backstop_if_unique_path_fails(self):
        self.make("Documents/report.pdf", "old")
        self.make("report.pdf", "new")

        def no_conflict_check(self_, destination, reserved=()):
            return destination  # pretend the name is always free

        organizer = self.organizer(dry_run=False)
        with mock.patch.object(
            FileOrganizer, "_unique_path", no_conflict_check
        ):
            summary = organizer.organize_directory()

        self.assertEqual(summary, {})
        self.assertIsInstance(organizer.failures[0][1], FileExistsError)
        self.assertEqual(self.read("Documents/report.pdf"), "old")
        self.assertEqual(self.read("report.pdf"), "new")


if __name__ == "__main__":
    unittest.main()
