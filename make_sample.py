"""Create a messy sample folder for demonstrating the Smart File Organizer.

Usage:  python make_sample.py [folder]        (default: sample_folder)

The random seed is fixed, so every run produces identical files.
"""

import random
import sys
from pathlib import Path

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("sample_folder")
if root.exists() and any(root.iterdir()):
    sys.exit(
        f"{root} already exists and is not empty. Delete it or choose another name."
    )

rng = random.Random(42)
created = []


def unique(name, size=300):
    """Content that is different for every file name."""
    return f"sample file: {name}\n".encode("utf-8") + rng.randbytes(size)


def write(relative, data):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    created.append(relative)
    return data


# 1. one file of every kind at the top level
TOP_LEVEL = [
    "report.pdf",
    "notes.txt",
    "budget.xlsx",
    "slides.pptx",
    "thesis.docx",
    "letter.odt",  # Documents
    "photo1.jpg",
    "holiday.JPG",
    "logo.png",
    "banner.gif",
    "icon.svg",
    "scan.jpeg",  # Images
    "song.mp3",
    "podcast.wav",
    "ringtone.ogg",
    "album.flac",  # Audio
    "clip.mp4",
    "movie.mkv",
    "old.avi",
    "trailer.mov",  # Videos
    "backup.zip",
    "source.tar",
    "logs.gz",
    "data.rar",  # Archives
    "script.py",
    "app.js",
    "Main.java",
    "engine.cpp",
    "index.html",
    "style.css",  # Code
    "README",
    "data.bin",
    "setup.exe",
    "todo.md",  # Others
    "my holiday photo.png",
    "café menu.pdf",
    "résumé.docx",  # spaces, accents
]
content = {name: write(name, unique(name)) for name in TOP_LEVEL}

# 2. exact duplicates (same content, different place or name)
write(
    "downloads/photo1.jpg", content["photo1.jpg"]
)  # same name AND same content
write("music/song_copy.mp3", content["song.mp3"])
write(
    "music/podcast.wav", content["podcast.wav"]
)  # same name AND same content
write("backup/backup.zip", content["backup.zip"])
write(
    "backup/old_backup.zip", content["backup.zip"]
)  # with the top-level copy: a group of three

# 3. name conflicts with DIFFERENT content (they become report_1.pdf and so on)
for relative in [
    "downloads/report.pdf",
    "work/2024/budget.xlsx",
    "work/old/notes.txt",
    "work/old/script.py",
]:
    write(relative, unique(relative))

# 4. other nested files, including a folder named like a category
for relative in [
    "work/2024/summary.docx",
    "trips/Images/beach.png",
    "trips/Images/sunset.jpg",
    "photos/IMG_0001.jpg",
    "photos/IMG_0002.jpg",
    "photos/IMG_0003.jpg",
]:
    write(relative, unique(relative))

# 5. same size, different content: the duplicate detector must NOT report these
write("twin_a.txt", b"A" * 100)
write("twin_b.txt", b"B" * 100)

# 6. empty files (ignored by the duplicate detector by default)
write("empty1.txt", b"")
write("empty2.txt", b"")

# 7. already sorted: the organizer must leave this file alone
write("Documents/already_sorted.pdf", unique("already_sorted.pdf"))

# 8. folders that every command skips by default
for relative in [
    "node_modules/pkg/index.js",
    "node_modules/pkg/logo.png",
    "logs/app.log",
    "logs/error.log",
    "AppData/cache/temp.dat",
]:
    write(relative, unique(relative))

print(f"Created {len(created)} files in {root}")
