from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from infra.config.loader import get_config_and_env


def _connection_kwargs() -> dict:
    config = get_config_and_env()
    return {
        "host": config["DB_HOST"],
        "dbname": config["DB_NAME"],
        "port": int(config.get("DB_PORT") or 5432),
        "user": config["DB_LOGIN"],
        "password": config["DB_PASSWORD"],
        "connect_timeout": int(os.environ.get("DB_CONNECT_TIMEOUT", "20")),
    }


@contextmanager
def connect() -> Iterator[psycopg.Connection]:
    with psycopg.connect(**_connection_kwargs(), row_factory=dict_row) as conn:
        yield conn


def fetch_mtrs(gids: list[int]) -> list[dict]:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT gid, eos_id, class_code
                FROM nci.mtrs
                WHERE gid = ANY(%s)
                ORDER BY gid
                """,
                (gids,),
            )
            return cur.fetchall()


def fetch_class_attribute_sets(class_codes: list[str]) -> dict[str, list[dict]]:
    with connect() as conn:
        with conn.cursor() as cur:
            result: dict[str, list[dict]] = {}
            for class_code in sorted(set(class_codes)):
                cur.execute(
                    """
                    SELECT
                        ca.attr_id,
                        COALESCE(a.attr_name, ca.src_attr_name) AS attr_name,
                        a.attr_type,
                        a.descr,
                        ca.req_data,
                        ca.req_attr,
                        ca.is_main
                    FROM nci.class_attrs ca
                    LEFT JOIN nci.attrs a ON a.attr_id = ca.attr_id
                    WHERE ca.class_code = %s
                    ORDER BY ca.ord_full NULLS LAST, ca.src_attr_name
                    """,
                    (class_code,),
                )
                result[class_code] = cur.fetchall()
            return result


def fetch_attr_details(class_codes: list[str]) -> dict[tuple[str, str], dict]:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    class_code,
                    attr_id,
                    data_type,
                    units,
                    unit_type,
                    val_text
                FROM nci.attr_details
                WHERE class_code = ANY(%s)
                """,
                (sorted(set(class_codes)),),
            )
            return {
                (row["class_code"], row["attr_id"]): row
                for row in cur.fetchall()
                if row["class_code"] is not None and row["attr_id"] is not None
            }


def fetch_ground_truth(gids: list[int]) -> list[dict]:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT ON (gid, attr_id)
                    gid,
                    attr_id,
                    src_attr_name AS attr_name,
                    attr_val AS value
                FROM nci.mtr_attr_vals
                WHERE gid = ANY(%s)
                ORDER BY gid, attr_id, src_file DESC, id DESC
                """,
                (gids,),
            )
            return cur.fetchall()
