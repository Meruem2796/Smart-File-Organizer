from organizer.scanner import FileScanner

s = FileScanner(
    ".", recursive=True, excluded_directories=[".git", "__pycache__"]
)
s.scan_directory()
for p in s.iter_files():
    print(s.get_file_metadata(p))
