# Smart File Organizer: report

## 1. How do your classes communicate, and why composition?

`main.py` creates the objects and passes data between them. `FileOrganizer` receives
a `FileClassifier` in its constructor (the organizer *has a* classifier), creates a
`FileScanner` to find files, and uses one `FileMover` per file. `DuplicateDetector`
receives only a list of paths (`scanner.files`), so it does not know the scanner exists.

Composition fits because an organizer is not a kind of classifier or scanner; it
uses them. Each class has one job, a classifier with custom rules can be passed in
without touching the organizer, and each class is tested alone. Inheritance would tie
them together. The organizer builds its scanner and mover itself, so those two are
less swappable than the classifier.

## 2. How does your registration decorator work?

`register_category(name)` is a decorator *factory*. Calling it with a name returns
`decorator(func)`, which stores `func` in `self.rules[name]` and returns `func`
unchanged. A closure keeps `name` and `self` alive between the two calls. So
`@classifier.register_category("Notes")` above a function is the same as
`register_category("Notes")(is_note)`. The name is validated on the `@` line, before
the function is stored, because it later becomes a folder name. Rules are kept in a
dictionary, so they are checked in registration order and the first match wins.

## 3. What is the difference between `return` and `yield`, and why a generator for scanning?

`return` ends the function and hands back one value. `yield` hands back one value and
pauses, keeping its local state, until the loop asks for the next one. In
`iter_files()`, `for path in scanner.iter_files()` receives paths one at a time instead
of getting another copy of the list. A generator keeps memory small and lets the caller
stop early. In my version `scan_directory()` still builds a full list first (the spec's
file-list contract), so the memory benefit is limited. The list is deliberate: the
organizer moves files while looping, and moving files while still walking the folder
tree is unsafe.

## 4. What happens when an exception occurs inside a `with` block?

Python still calls `__exit__(exc_type, exc, tb)`. In `FileMover` it records `end_time`,
sets `status = "failed"` and stores the error. It returns `False`, so the exception
continues upward instead of being hidden. (Returning `True` would swallow it.)
`FileOrganizer.organize_directory` then catches the `OSError`, logs it, records the file
in `failures`, and carries on with the next file. The exit code becomes 1.

## 5. Why hash files in chunks?

Reading a whole file at once needs as much memory as the file: a 4 GB video would need
4 GB of RAM. Reading fixed-size chunks and calling `hasher.update(chunk)` keeps memory
constant and gives the same SHA-256 digest (my test compares the chunked hash with
`hashlib.sha256(data)`). Small chunks mean many slow read calls and large chunks use
more memory, so the CLI uses 1 MB. The detector also groups by size first, so most files
are never hashed.