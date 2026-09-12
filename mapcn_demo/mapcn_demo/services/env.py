"""Reads the optional API keys of the demo from a local ``.env`` file.

Reflex only loads a dotenv file when the config asks for it and the
``python-dotenv`` package is installed, and a demo is a poor reason to add a
dependency for two keys. This parses the handful of lines the file can hold:
``KEY=value``, comments, blanks, and quotes around a value.

A variable already exported in the shell always wins, which is what anyone
debugging a key expects.
"""

from __future__ import annotations

import os
import pathlib

#: The demo's own file, beside `rxconfig.py`.
DEFAULT_ENV_PATH = pathlib.Path(__file__).resolve().parents[2] / ".env"


def read_env_file(path: str | pathlib.Path) -> dict[str, str]:
    """The settings in ``path``, or nothing when there is no such file."""
    file = pathlib.Path(path)
    if not file.is_file():
        return {}

    values: dict[str, str] = {}
    for line in file.read_text().splitlines():
        setting = line.strip()
        if not setting or setting.startswith("#") or "=" not in setting:
            continue
        name, _, value = setting.partition("=")
        values[name.strip()] = value.strip().strip("\"'")
    return values


def load_env_file(
    path: str | pathlib.Path = DEFAULT_ENV_PATH,
    environ: dict[str, str] | None = None,
) -> dict[str, str]:
    """Add the file's settings to the environment without overriding it."""
    target = os.environ if environ is None else environ
    values = read_env_file(path)
    for name, value in values.items():
        target.setdefault(name, value)
    return values


def api_key(name: str) -> str:
    """The value of one key, empty when it was never set."""
    return os.environ.get(name, "").strip()
