from pathlib import Path

from organizer.scanner import FileScanner


class FileOrganizer:
    def __init__(self, source_directory, classifier, dry_run=False):
        self.source_directory = Path(source_directory)
        self._check_source()
        self.classifier = (
            classifier  # composition: the organizer HAS a classifier
        )
        self.dry_run = dry_run
        self._planned = set()  # destinations already promised in a dry run

    def _check_source(self):
        resolved = self.source_directory.resolve()
        if not resolved.is_dir():
            raise NotADirectoryError(
                f"Not a directory: {self.source_directory}"
            )
        if resolved == resolved.parent or resolved == Path.home().resolve():
            raise ValueError(
                f"Refusing to organize a root or home folder: {resolved}"
            )

    def _scan(self):
        scanner = FileScanner(self.source_directory, recursive=True)
        category_folders = {
            name.casefold() for name in self.classifier.get_categories()
        }
        files = []
        for path in scanner.scan_directory():
            parts = path.relative_to(self.source_directory).parts
            # ignore files already inside a TOP-LEVEL category folder.
            # len(parts) > 1 matters: for a root file, parts[0] is the file name itself
            if len(parts) > 1 and parts[0].casefold() in category_folders:
                continue
            files.append(path)
        return files

    def _destination(self, path):
        category = self.classifier.classify_file(path)
        destination = self.source_directory / category / path.name
        if not destination.resolve().is_relative_to(
            self.source_directory.resolve()
        ):
            raise ValueError(
                f"Destination escapes the source folder: {destination}"
            )
        return destination

    def _unique_path(self, destination, reserved=()):
        candidate, counter = destination, 1
        while (
            candidate.exists() or candidate in reserved
        ):  # report.pdf -> report_1.pdf -> ...
            name = f"{destination.stem}_{counter}{destination.suffix}"
            candidate = destination.with_name(name)
            counter += 1
        return candidate

    def preview_organization(self):
        reserved, plan = set(), []
        for path in self._scan():
            destination = self._unique_path(self._destination(path), reserved)
            reserved.add(
                destination
            )  # the next file with the same name must not reuse it
            plan.append((path, destination))
        return plan

    def organize_file(self, path):
        destination = self._unique_path(self._destination(path), self._planned)
        if self.dry_run:
            self._planned.add(destination)
            return destination  # pretend: change nothing
        raise NotImplementedError("Real moves arrive in Stage 4")

    def organize_directory(self):
        self._planned = set()  # fresh plan for every run
        summary = {}
        for (
            path
        ) in (
            self._scan()
        ):  # _scan returns a list, so it is safe to change files later
            category = self.classifier.classify_file(path)
            self.organize_file(path)
            summary[category] = summary.get(category, 0) + 1
        return summary
