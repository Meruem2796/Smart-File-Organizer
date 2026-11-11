from pathlib import Path
from organizer.classifier import FileClassifier

classifier = FileClassifier()


@classifier.register_category("Logs")
def is_log(path):
    return path.suffix.lower() == ".log"


for name in [
    "photo.PNG",
    "notes.txt",
    "app.log",
    "movie.mkv",
    "README",
    "backup.tar.gz",
]:
    print(f"{name:15} -> {classifier.classify_file(Path(name))}")
