"""Скачать небольшой HTTP-файл и сохранить его без изменений в raw."""

from __future__ import annotations

import logging
from typing import Any

import requests

from airflow.providers.amazon.aws.hooks.s3 import S3Hook

RAW_BUCKET = "raw"


def load_to_raw(
    *,
    source_url: str,
    source_filename: str,
    dataset_slug: str,
    s3_conn_id: str,
    **context: Any,
) -> None:
    """Загрузить исходный файл или оставить уже созданный raw-объект.

    Бакет ``raw`` создаёт инфраструктура при запуске стенда. Задача не создаёт
    его сама: если бакета нет, стенд не поднят и загрузка завершается ошибкой
    с понятным сообщением.
    """
    key = f"{dataset_slug}/ingested_on={context['ds']}/{source_filename}"
    s3_hook = S3Hook(aws_conn_id=s3_conn_id)

    if not s3_hook.check_for_bucket(bucket_name=RAW_BUCKET):
        message = (
            f"Бакет '{RAW_BUCKET}' не найден. Поднимите стенд командой "
            "'docker compose up -d' и дождитесь статуса healthy: "
            "SeaweedFS создаёт бакеты raw, staging и mart при запуске."
        )
        raise RuntimeError(message)

    if s3_hook.check_for_key(key=key, bucket_name=RAW_BUCKET):
        logging.info(
            "Raw object already exists and will not be modified: s3://%s/%s",
            RAW_BUCKET,
            key,
        )
        return

    response = requests.get(source_url, timeout=60)
    response.raise_for_status()
    s3_hook.load_bytes(
        bytes_data=response.content,
        key=key,
        bucket_name=RAW_BUCKET,
        replace=False,
    )
    logging.info("Downloaded HTTP file %s to s3://%s/%s", source_url, RAW_BUCKET, key)
