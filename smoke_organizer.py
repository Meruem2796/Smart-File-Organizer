import sys
from organizer.classifier import FileClassifier
from organizer.file_organizer import FileOrganizer

organizer = FileOrganizer(sys.argv[1], FileClassifier(), dry_run=True)
for source, destination in organizer.preview_organization():
    print(f"{source} -> {destination}")
print(organizer.organize_directory())
