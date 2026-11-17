import sys
from organizer.classifier import FileClassifier
from organizer.file_organizer import FileOrganizer

real = "--real" in sys.argv
folder = [arg for arg in sys.argv[1:] if arg != "--real"][0]

organizer = FileOrganizer(folder, FileClassifier(), dry_run=not real)
summary = organizer.organize_directory()
print("REAL RUN" if real else "DRY RUN", summary)
for path, error in organizer.failures:
    print("FAILED:", path, error)
