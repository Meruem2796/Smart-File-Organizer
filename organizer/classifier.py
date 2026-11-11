from pathlib import Path


class FileClassifier:
    DEFAULTS = {
        "Documents": {".pdf", ".docx", ".txt", ".odt", ".xlsx", ".pptx"},
        "Images": {".jpg", ".jpeg", ".png", ".gif", ".svg"},
        "Audio": {".mp3", ".wav", ".ogg", ".flac"},
        "Videos": {".mp4", ".mkv", ".avi", ".mov"},
        "Archives": {".zip", ".tar", ".gz", ".rar"},
        "Code": {".py", ".js", ".java", ".cpp", ".html", ".css"},
    }
    FALLBACK = "Others"
    FORBIDDEN_CHARS = set('<>:"/\\|?*')

    def __init__(self):
        self.rules = {}  # category name -> function(path) -> True/False
        for category, extensions in self.DEFAULTS.items():
            self.rules[category] = self._by_extension(extensions)

    @staticmethod
    def _by_extension(extensions):
        def rule(path):  # closure: remembers `extensions`
            return path.suffix.lower() in extensions

        return rule

    @classmethod
    def _validate_name(cls, name):
        # the name becomes a folder name, so it must be a safe single folder name
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Category name must be a non-empty string")
        if name != name.strip() or name.endswith("."):
            raise ValueError(f"Invalid category name: {name!r}")
        if any(char in cls.FORBIDDEN_CHARS for char in name):
            raise ValueError(
                f"Category name contains forbidden characters: {name!r}"
            )
        if name.casefold() == cls.FALLBACK.casefold():
            raise ValueError(
                f"{cls.FALLBACK!r} is reserved for unmatched files"
            )

    def register_category(self, name):  # layer 1: gets the category name
        self._validate_name(name)  # fails early, on the @ line

        def decorator(func):  # layer 2: gets the rule function
            self.rules[name] = func  # save it under that name
            return func  # give the function back unchanged

        return decorator

    def classify_file(self, path):
        path = Path(path)  # accept str or Path
        for name, rule in self.rules.items():
            if rule(path):  # first rule that says True wins
                return name
        return self.FALLBACK

    def get_categories(self):
        return list(self.rules) + [self.FALLBACK]
