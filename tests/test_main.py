import logging
import unittest
from pathlib import Path
from unittest import mock

import main
from organizer.file_mover import FileMover
from tests.helpers import OrganizerTestCase


class TestCommandLine(OrganizerTestCase):
    def test_scan_lists_files_with_metadata(self):
        self.make("a.txt", "abc")
        self.make("sub/b.png")
        code, out, _ = self.run_cli("scan", str(self.root))
        self.assertEqual(code, 0)
        self.assertIn("a.txt", out)
        self.assertIn(str(Path("sub") / "b.png"), out)
        self.assertIn("2 file(s)", out)

    def test_scan_skips_default_and_custom_excluded_folders(self):
        self.make("keep.txt")
        self.make(".git/config")
        self.make("node_modules/pkg/index.js")
        self.make("cache/tmp.txt")
        _, out, _ = self.run_cli("scan", str(self.root), "--exclude", "cache")
        self.assertIn("keep.txt", out)
        for hidden in ("config", "index.js", "tmp.txt"):
            self.assertNotIn(hidden, out)
        self.assertIn("1 file(s)", out)

    def test_organize_dry_run_prints_plan_and_changes_nothing(self):
        self.make("photo.png")
        self.make("notes.txt")
        before = self.snapshot()
        code, out, _ = self.run_cli("organize", str(self.root), "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn(f"photo.png -> {Path('Images') / 'photo.png'}", out)
        self.assertIn("Dry run: 2 file(s) would be moved", out)
        self.assertEqual(self.snapshot(), before)

    def test_organize_moves_files_and_second_run_moves_nothing(self):
        self.make("photo.png", "img")
        code, out, _ = self.run_cli("organize", str(self.root))
        self.assertEqual(code, 0)
        self.assertEqual(self.read("Images/photo.png"), "img")
        self.assertIn("Images: 1", out)
        code, out, _ = self.run_cli("organize", str(self.root))
        self.assertEqual(code, 0)
        self.assertIn("Moved 0 file(s)", out)

    def test_organize_failure_gives_exit_code_1(self):
        self.make("bad.png", "keep")
        self.make("good.txt", "moved")
        real_execute = FileMover.execute

        def flaky(mover):  # fails for one file, works for the rest
            if mover.source.name == "bad.png":
                raise PermissionError("file is locked")
            return real_execute(mover)

        with mock.patch.object(FileMover, "execute", flaky):
            code, _, err = self.run_cli("organize", str(self.root))
        self.assertEqual(code, 1)
        self.assertIn("FAILED", err)
        self.assertIn("bad.png", err)
        self.assertEqual(self.read("bad.png"), "keep")
        self.assertEqual(self.read("Documents/good.txt"), "moved")

    def test_duplicates_reports_groups_and_deletes_nothing(self):
        self.make("a/one.txt", "same")
        self.make("b/two.txt", "same")
        before = self.snapshot()
        code, out, _ = self.run_cli("duplicates", str(self.root))
        self.assertEqual(code, 0)
        self.assertIn("Group 1: 2 files", out)
        self.assertIn("one.txt", out)
        self.assertIn("two.txt", out)
        self.assertEqual(self.snapshot(), before)

    def test_missing_directory_gives_exit_code_2(self):
        code, _, err = self.run_cli("scan", str(self.root / "nope"))
        self.assertEqual(code, 2)
        self.assertIn("error:", err)

    def test_home_folder_is_refused(self):
        code, _, err = self.run_cli("organize", str(Path.home()), "--dry-run")
        self.assertEqual(code, 2)
        self.assertIn("Refusing", err)

    def test_path_with_spaces_works_when_passed_as_one_argument(self):
        self.make("My Files/a.png")
        code, out, _ = self.run_cli(
            "organize", str(self.root / "My Files"), "--dry-run"
        )
        self.assertEqual(code, 0)
        self.assertIn("1 file(s) would be moved", out)

    def test_unquoted_path_with_spaces_is_a_usage_error(self):
        code, _, err = self.run_cli("scan", str(self.root / "My"), "Files")
        self.assertEqual(code, 2)
        self.assertIn("unrecognized arguments", err)

    def test_invalid_chunk_size_is_a_usage_error(self):
        code, _, err = self.run_cli(
            "duplicates", str(self.root), "--chunk-size", "0"
        )
        self.assertEqual(code, 2)
        self.assertIn("greater than 0", err)

    def test_unknown_command_is_a_usage_error(self):
        code, _, _ = self.run_cli("explode", str(self.root))
        self.assertEqual(code, 2)

    def test_dry_run_flag_only_exists_for_organize(self):
        code, _, _ = self.run_cli("scan", str(self.root), "--dry-run")
        self.assertEqual(code, 2)

    def test_verbose_flag_enables_debug_logging(self):
        self.run_cli("-v", "scan", str(self.root))
        self.assertEqual(
            self.basic_config.call_args.kwargs["level"], logging.DEBUG
        )
        self.run_cli("scan", str(self.root))
        self.assertEqual(
            self.basic_config.call_args.kwargs["level"], logging.INFO
        )

    def test_command_is_logged_and_timed(self):
        with self.assertLogs("organizer.decorators", level="INFO") as logs:
            _, _, err = self.run_cli("scan", str(self.root))
        self.assertTrue(
            any("run_scan succeeded" in line for line in logs.output)
        )
        self.assertIn("run_scan took", err)

    def test_handlers_keep_their_names(self):
        self.assertEqual(main.run_scan.__name__, "run_scan")
        self.assertEqual(main.run_organize.__name__, "run_organize")
        self.assertEqual(main.run_duplicates.__name__, "run_duplicates")


if __name__ == "__main__":
    unittest.main()
