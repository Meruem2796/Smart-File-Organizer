import unittest
from pathlib import Path

from organizer.classifier import FileClassifier


class TestFileClassifier(unittest.TestCase):
    def setUp(self):
        self.classifier = FileClassifier()

    def test_default_extensions(self):
        expected = {
            "report.pdf": "Documents",
            "photo.png": "Images",
            "song.mp3": "Audio",
            "clip.mkv": "Videos",
            "backup.zip": "Archives",
            "script.py": "Code",
        }
        for name, category in expected.items():
            with self.subTest(name=name):
                self.assertEqual(
                    self.classifier.classify_file(Path(name)), category
                )

    def test_extension_is_case_insensitive(self):
        self.assertEqual(
            self.classifier.classify_file(Path("PHOTO.PNG")), "Images"
        )

    def test_unknown_and_no_extension_are_others(self):
        self.assertEqual(
            self.classifier.classify_file(Path("data.xyz")), "Others"
        )
        self.assertEqual(
            self.classifier.classify_file(Path("README")), "Others"
        )

    def test_double_extension_uses_last_suffix(self):
        self.assertEqual(
            self.classifier.classify_file(Path("backup.tar.gz")), "Archives"
        )

    def test_accepts_string_path(self):
        self.assertEqual(self.classifier.classify_file("photo.png"), "Images")

    def test_custom_category_via_decorator(self):
        @self.classifier.register_category("Logs")
        def is_log(path):
            return path.suffix.lower() == ".log"

        self.assertEqual(
            self.classifier.classify_file(Path("app.log")), "Logs"
        )

    def test_decorator_returns_function_unchanged(self):
        def is_log(path):
            return path.suffix == ".log"

        decorated = self.classifier.register_category("Logs")(is_log)
        self.assertIs(decorated, is_log)

    def test_registering_existing_name_replaces_rule(self):
        self.classifier.register_category("Images")(
            lambda p: p.suffix == ".xyz"
        )
        self.assertEqual(
            self.classifier.classify_file(Path("a.xyz")), "Images"
        )
        self.assertEqual(
            self.classifier.classify_file(Path("a.png")), "Others"
        )

    def test_first_registered_match_wins(self):
        # "Screenshots" is registered AFTER the defaults, so "Images" matches first
        self.classifier.register_category("Screenshots")(
            lambda p: p.name.startswith("Screenshot")
        )
        self.assertEqual(
            self.classifier.classify_file(Path("Screenshot1.png")), "Images"
        )
        self.assertEqual(
            self.classifier.classify_file(Path("Screenshot1.bmp")),
            "Screenshots",
        )

    def test_get_categories(self):
        self.classifier.register_category("Logs")(lambda p: False)
        categories = self.classifier.get_categories()
        self.assertEqual(categories[-1], "Others")
        self.assertIn("Logs", categories)
        self.assertEqual(
            len(categories), len(set(categories))
        )  # no duplicates

    def test_invalid_names_rejected(self):
        bad_names = [
            "",
            "   ",
            "..",
            "a/b",
            "a\\b",
            "C:x",
            " Images",
            "Images.",
            "Others",
            "others",
        ]
        for name in bad_names:
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    self.classifier.register_category(name)

    def test_instances_do_not_share_rules(self):
        self.classifier.register_category("Logs")(lambda p: True)
        self.assertNotIn("Logs", FileClassifier().get_categories())


if __name__ == "__main__":
    unittest.main()
