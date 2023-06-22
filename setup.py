"""Setup.py for editable install."""

# Generated features:
# - editable mode with a setup.cfg
# - offline git support via url replacement to point at the local file system.
# - package custom executables found in <package-dir>/scripts

from __future__ import annotations

from os import X_OK, access
from pathlib import Path

from setuptools import setup


def find_package_dir() -> Path:
    """Find the package dir from setup.cfg's "where = " entry."""
    return dirs_from_lines_with_prefix(Path("setup.cfg"), "where = ")[0]


def dirs_from_lines_with_prefix(filename: Path, prefix: str) -> tuple[Path, ...]:
    """If the file does not exist, return empty string.

    Otherwise, return lines matching query
    """
    root = Path().absolute()

    if not filename.is_file():
        return ()

    contents = filename.read_text(encoding="utf-8")
    if not contents:
        return ()

    if prefix and prefix not in contents:
        return ()

    return tuple(
        Path(path_).absolute().relative_to(root)
        for line_ in contents.splitlines()
        if line_.strip().startswith(prefix)
        and (path_ := Path(line_.strip().removeprefix(prefix))).is_dir()
    )


def find_scripts() -> tuple[str, ...]:
    """Search the package for scripts in a directory called "scripts"."""
    root = Path().absolute()

    scripts_dirname = "scripts"

    package_dir = find_package_dir()

    discovered_scripts: list[str] = []
    for path_ in Path(package_dir).iterdir():
        if (scripts_dir := path_ / scripts_dirname).is_dir():
            for script_ in scripts_dir.iterdir():
                if script_.is_file() and access(script_, X_OK):
                    discovered_scripts.append(str(script_.absolute().relative_to(root)))
    return tuple(discovered_scripts)


if __name__ == "__main__":
    packaged_scripts = list(find_scripts())

    # install this package, possibly overriding dependencies of extra requirements
    setup(scripts=packaged_scripts)
