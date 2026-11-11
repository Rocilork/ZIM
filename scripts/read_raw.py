"""Запустить проверку доступности raw-файла через DuckDB."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    """Добавить исходный каталог проекта и передать выполнение модулю анализа."""
    source_directory = Path(__file__).resolve().parents[1] / "src"
    sys.path.insert(0, str(source_directory))

    from analysis.read_raw import main as read_raw_main

    read_raw_main()


if __name__ == "__main__":
    main()
