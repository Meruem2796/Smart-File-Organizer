import hashlib
import unittest
from unittest import mock

from organizer.duplicate_detector import DuplicateDetector
from organizer.scanner import FileScanner
from tests.helpers import OrganizerTestCase


class TestDuplicateDetector(OrganizerTestCase):
    def test_identical_files_are_grouped(self):
        a = self.make("a.txt", "same")
        b = self.make("b.txt", "same")
        c = self.make("c.txt", "diff")
        groups = DuplicateDetector([a, b, c]).find_duplicates()
        self.assertEqual(groups, [[a, b]])

    def test_same_size_different_content_is_not_a_duplicate(self):
        a = self.make("a.txt", "abcd")
        b = self.make("b.txt", "abce")
        self.assertEqual(DuplicateDetector([a, b]).find_duplicates(), [])

    def test_unique_sizes_are_never_hashed(self):
        a = self.make("a.txt", "x")
        b = self.make("b.txt", "yy")
        with mock.patch.object(
            DuplicateDetector, "calculate_file_hash"
        ) as fake_hash:
            DuplicateDetector([a, b]).find_duplicates()
        fake_hash.assert_not_called()

    def test_three_identical_files_form_one_group(self):
        files = [self.make(f"{name}.txt", "same") for name in "abc"]
        groups = DuplicateDetector(files).find_duplicates()
        self.assertEqual(groups, [files])

    def test_two_separate_groups(self):
        a1 = self.make("a1.txt", "aaaa")
        a2 = self.make("a2.txt", "aaaa")
        b1 = self.make("b1.txt", "bbbbbb")
        b2 = self.make("b2.txt", "bbbbbb")
        groups = DuplicateDetector([a1, b1, a2, b2]).find_duplicates()
        self.assertEqual(groups, [[a1, a2], [b1, b2]])

    def test_difference_after_first_chunk_is_detected(self):
        a = self.make("a.txt", "aaaaX")
        b = self.make("b.txt", "aaaaY")  # same first chunk, different ending
        c = self.make("c.txt", "aaaaX")
        groups = DuplicateDetector([a, b, c], chunk_size=4).find_duplicates()
        self.assertEqual(groups, [[a, c]])

    def test_hash_matches_sha256_for_chunked_reads(self):
        data = b"abcdefghij"  # 10 bytes, chunk_size 3: 3+3+3+1
        path = self.root / "data.bin"
        path.write_bytes(data)
        detector = DuplicateDetector([path], chunk_size=3)
        self.assertEqual(
            detector.calculate_file_hash(path),
            hashlib.sha256(data).hexdigest(),
        )

    def test_invalid_chunk_size_rejected(self):
        for bad in (0, -1, "4", 1.5, None):
            with self.subTest(chunk_size=bad):
                with self.assertRaises(ValueError):
                    DuplicateDetector([], chunk_size=bad)

    def test_empty_files_ignored_by_default(self):
        a = self.make("a.txt", "")
        b = self.make("b.txt", "")
        self.assertEqual(DuplicateDetector([a, b]).find_duplicates(), [])

    def test_empty_files_can_be_included(self):
        a = self.make("a.txt", "")
        b = self.make("b.txt", "")
        groups = DuplicateDetector(
            [a, b], include_empty=True
        ).find_duplicates()
        self.assertEqual(groups, [[a, b]])

    def test_missing_file_is_skipped_not_fatal(self):
        a = self.make("a.txt", "same")
        b = self.make("b.txt", "same")
        ghost = self.root / "ghost.txt"
        detector = DuplicateDetector([a, ghost, b])
        self.assertEqual(detector.find_duplicates(), [[a, b]])
        self.assertEqual(
            [path.name for path, _ in detector.skipped], ["ghost.txt"]
        )
        self.assertIsInstance(detector.skipped[0][1], FileNotFoundError)

    def test_unreadable_file_is_skipped_not_fatal(self):
        a = self.make("a.txt", "same")
        b = self.make("b.txt", "same")
        c = self.make("c.txt", "same")
        real_hash = DuplicateDetector.calculate_file_hash

        def flaky(
            detector_self, path
        ):  # fails for one file, works for the rest
            if path.name == "c.txt":
                raise PermissionError("file is locked")
            return real_hash(detector_self, path)

        detector = DuplicateDetector([a, b, c])
        with mock.patch.object(
            DuplicateDetector, "calculate_file_hash", flaky
        ):
            groups = detector.find_duplicates()
        self.assertEqual(groups, [[a, b]])
        self.assertEqual(
            [path.name for path, _ in detector.skipped], ["c.txt"]
        )

    def test_folder_in_input_is_skipped(self):
        a = self.make("a.txt", "same")
        b = self.make("b.txt", "same")
        folder = self.root / "sub"
        folder.mkdir()
        detector = DuplicateDetector([a, folder, b])
        self.assertEqual(detector.find_duplicates(), [[a, b]])
        self.assertEqual(detector.skipped, [(folder, "not a regular file")])

    def test_symlink_is_skipped(self):
        target = self.make("real.txt", "same")
        link = self.root / "link.txt"
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest(
                "symlinks not available (Windows needs Developer Mode or admin)"
            )
        detector = DuplicateDetector([target, link])
        self.assertEqual(detector.find_duplicates(), [])
        self.assertEqual([path for path, _ in detector.skipped], [link])

    def test_same_path_listed_twice_is_not_a_duplicate(self):
        a = self.make("a.txt", "same")
        detector = DuplicateDetector([a, a])
        self.assertEqual(len(detector.files), 1)
        self.assertEqual(detector.find_duplicates(), [])

    def test_finding_duplicates_deletes_nothing(self):
        a = self.make("a.txt", "same")
        b = self.make("b.txt", "same")
        before = self.snapshot()
        detector = DuplicateDetector([a, b])
        detector.find_duplicates()
        detector.generate_duplicate_report()
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(a.read_text(), "same")
        self.assertEqual(b.read_text(), "same")

    def test_groups_are_sorted_and_stable(self):
        a = self.make("a/x.txt", "same")
        b = self.make("b/x.txt", "same")
        groups = DuplicateDetector(
            [b, a]
        ).find_duplicates()  # given in reverse order
        self.assertEqual(groups, [[a, b]])

    def test_report_without_duplicates(self):
        a = self.make("a.txt", "one")
        b = self.make("b.txt", "two")
        detector = DuplicateDetector([a, b])
        detector.find_duplicates()
        self.assertEqual(
            detector.generate_duplicate_report(), "No duplicates found."
        )

    def test_report_lists_groups_and_savings(self):
        a = self.make("a.txt", "abcd")
        b = self.make("b.txt", "abcd")
        detector = DuplicateDetector([a, b])
        detector.find_duplicates()
        report = detector.generate_duplicate_report()
        self.assertIn("Group 1: 2 files, 4 bytes each", report)
        self.assertIn(str(a), report)
        self.assertIn(str(b), report)
        self.assertIn("4 bytes could be reclaimed", report)
        self.assertIn("Nothing was deleted", report)

    def test_report_mentions_skipped_files(self):
        a = self.make("a.txt", "one")
        detector = DuplicateDetector([a, self.root / "ghost.txt"])
        detector.find_duplicates()
        self.assertIn("Skipped 1 file", detector.generate_duplicate_report())

    def test_works_with_scanner_output(self):
        self.make("a/one.txt", "same")
        self.make("b/two.txt", "same")
        self.make("c/three.txt", "diff")
        scanner = FileScanner(self.root, recursive=True)
        scanner.scan_directory()
        groups = DuplicateDetector(scanner.files).find_duplicates()
        self.assertEqual(len(groups), 1)
        self.assertEqual(
            {path.name for path in groups[0]}, {"one.txt", "two.txt"}
        )


if __name__ == "__main__":
    unittest.main()
