import argparse
import logging
import sys
from collections import Counter

from organizer.classifier import FileClassifier
from organizer.decorators import log_operation, measure_execution_time
from organizer.duplicate_detector import DuplicateDetector
from organizer.file_organizer import FileOrganizer
from organizer.scanner import DEFAULT_EXCLUDED_DIRECTORIES, FileScanner

EXIT_OK = 0
EXIT_PARTIAL = 1  # finished, but some files could not be moved
EXIT_ERROR = 2  # could not run: bad folder, refused folder, bad option
DEFAULT_CHUNK_SIZE = (
    1024 * 1024
)  # 1 MB reads are much faster than 4 KB for big files


def _excluded(args):
    return DEFAULT_EXCLUDED_DIRECTORIES + tuple(args.exclude)


def _print_summary(counts):
    for category, count in sorted(counts.items()):
        print(f"  {category}: {count}")


# Stacking: the decorator closest to `def` wraps first, so the timer is inside
# and the logger is outside. The logger sees whatever the timer lets through.


@log_operation
@measure_execution_time
def run_scan(args):
    scanner = FileScanner(
        args.directory, recursive=True, excluded_directories=_excluded(args)
    )
    scanner.scan_directory()
    count = 0
    for path in scanner.iter_files():
        meta = scanner.get_file_metadata(path)
        if meta is None:
            continue  # vanished or unreadable since the scan
        print(
            f"{meta['size']:>12,}  {meta['modified']:%Y-%m-%d %H:%M}  "
            f"{path.relative_to(scanner.directory)}"
        )
        count += 1
    print(f"{count} file(s)")
    return EXIT_OK


@log_operation
@measure_execution_time
def run_organize(args):
    organizer = FileOrganizer(
        args.directory,
        FileClassifier(),
        dry_run=args.dry_run,
        excluded_directories=_excluded(args),
    )
    base = organizer.source_directory

    if args.dry_run:
        plan = organizer.preview_organization()
        for source, destination in plan:
            print(
                f"{source.relative_to(base)} -> {destination.relative_to(base)}"
            )
        _print_summary(
            Counter(destination.parent.name for _, destination in plan)
        )
        print(
            f"Dry run: {len(plan)} file(s) would be moved. Nothing was changed."
        )
        return EXIT_OK

    summary = organizer.organize_directory()
    _print_summary(summary)
    print(f"Moved {sum(summary.values())} file(s).")
    for path, error in organizer.failures:
        print(f"FAILED: {path}: {error}", file=sys.stderr)
    if organizer.failures:
        print(
            f"{len(organizer.failures)} file(s) could not be moved.",
            file=sys.stderr,
        )
        return EXIT_PARTIAL
    return EXIT_OK


@log_operation
@measure_execution_time
def run_duplicates(args):
    scanner = FileScanner(
        args.directory, recursive=True, excluded_directories=_excluded(args)
    )
    scanner.scan_directory()
    detector = DuplicateDetector(scanner.files, chunk_size=args.chunk_size)
    detector.find_duplicates()
    print(detector.generate_duplicate_report())
    return EXIT_OK


def _positive_int(text):
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"{text!r} is not a whole number"
        ) from None
    if value <= 0:
        raise argparse.ArgumentTypeError("must be greater than 0")
    return value


def build_parser():
    parser = argparse.ArgumentParser(
        prog="main.py", description="Smart File Organizer"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="show debug details (put it before the command)",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    def add_command(name, handler, help_text):
        sub = commands.add_parser(name, help=help_text)
        sub.add_argument(
            "directory",
            help="folder to work on (use quotes if the path has spaces)",
        )
        sub.add_argument(
            "--exclude",
            action="append",
            default=[],
            metavar="NAME",
            help="also skip folders with this name (repeatable)",
        )
        sub.set_defaults(handler=handler)
        return sub

    add_command("scan", run_scan, "list every file in a folder")
    organize = add_command(
        "organize", run_organize, "sort files into category folders"
    )
    organize.add_argument(
        "--dry-run", action="store_true", help="show the plan and move nothing"
    )
    duplicates = add_command(
        "duplicates", run_duplicates, "report identical files (never deletes)"
    )
    duplicates.add_argument(
        "--chunk-size",
        type=_positive_int,
        default=DEFAULT_CHUNK_SIZE,
        metavar="BYTES",
        help="bytes read per step when hashing",
    )
    return parser


def _make_output_safe():
    # a file name the console cannot display must not crash the program
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(errors="replace")


def main(argv=None):
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )
    _make_output_safe()
    try:
        return args.handler(args)
    except (
        OSError,
        ValueError,
    ) as error:  # missing folder, refused folder, bad value
        print(f"error: {error}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
