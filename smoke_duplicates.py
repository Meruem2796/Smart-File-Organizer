import sys
from organizer.duplicate_detector import DuplicateDetector
from organizer.scanner import FileScanner

scanner = FileScanner(sys.argv[1], recursive=True)
scanner.scan_directory()
detector = DuplicateDetector(
    scanner.files, chunk_size=1024 * 1024
)  # 1 MB chunks are faster
detector.find_duplicates()
print(detector.generate_duplicate_report())
