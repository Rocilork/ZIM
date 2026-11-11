"""Прочитать raw-объект из SeaweedFS через DuckDB без создания таблиц."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import duckdb

# Источник UCI опубликован в cp1252: в строке заголовка стоит байт 0xB0 (знак
# градуса) в именах температурных полей. Данные при этом содержат только ASCII.
# Поэтому для CSV заголовок пропускается, а имена столбцов задаются явно:
# так файл читается и старым DuckDB, у которого ещё нет параметра encoding.
CSV_HEADER_SKIP = 1
CSV_COLUMN_NAMES = (
    "Date",
    "Rented Bike Count",
    "Hour",
    "Temperature(\u00b0C)",
    "Humidity(%)",
    "Wind speed (m/s)",
    "Visibility (10m)",
    "Dew point temperature(\u00b0C)",
    "Solar Radiation (MJ/m2)",
    "Rainfall(mm)",
    "Snowfall (cm)",
    "Seasons",
    "Holiday",
    "Functioning Day",
)


def reader_for(filename: str) -> str:
    """Выбрать DuckDB table function по расширению исходного файла."""
    suffix = Path(filename).suffix.lower()
    readers = {
        ".csv": "read_csv",
        ".json": "read_json_auto",
        ".jsonl": "read_json_auto",
        ".ndjson": "read_json_auto",
        ".parquet": "read_parquet",
    }
    try:
        return readers[suffix]
    except KeyError as error:
        message = f"Для формата {suffix or 'без расширения'} не задан DuckDB reader."
        raise ValueError(message) from error


def query_for(object_path: str, limit: int = 5) -> tuple[str, list[object]]:
    """Собрать SQL для чтения объекта и параметры запроса.

    Для CSV явно задаются имена столбцов исходного файла, поэтому заголовок в
    cp1252 не мешает чтению, а объект в raw читается без изменений.
    """
    reader = reader_for(object_path)
    if reader == "read_csv":
        names = ", ".join(f"'{name}'" for name in CSV_COLUMN_NAMES)
        sql = (
            f"SELECT * FROM {reader}(?, skip={CSV_HEADER_SKIP}, header=false, "
            f"column_names=[{names}], auto_detect=true) LIMIT {int(limit)}"
        )
        return sql, [object_path]
    sql = f"SELECT * FROM {reader}(?) LIMIT {int(limit)}"
    return sql, [object_path]


def configure_s3(connection: duckdb.DuckDBPyConnection) -> None:
    """Настроить S3-совместимый доступ DuckDB к локальному SeaweedFS."""
    endpoint = os.getenv("S3_ENDPOINT", "localhost:8333")
    access_key = os.getenv("S3_ACCESS_KEY", "s3admin")
    secret_key = os.getenv("S3_SECRET_KEY", "s3admin123")

    connection.execute("INSTALL httpfs")
    connection.execute("LOAD httpfs")
    connection.execute(f"SET s3_endpoint = '{endpoint}'")
    connection.execute("SET s3_url_style = 'path'")
    connection.execute("SET s3_use_ssl = false")
    connection.execute(f"SET s3_access_key_id = '{access_key}'")
    connection.execute(f"SET s3_secret_access_key = '{secret_key}'")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", required=True, help="S3-путь к raw-объекту.")
    args = parser.parse_args()

    connection = duckdb.connect()
    configure_s3(connection)

    sql, parameters = query_for(args.path)
    rows = connection.execute(sql, parameters).fetchall()
    columns = [description[0] for description in connection.description]
    print(" | ".join(columns))
    for row in rows:
        print(row)


if __name__ == "__main__":
    main()
