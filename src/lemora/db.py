import os

import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ.get("LEMORA_DATABASE_URL", "postgresql://localhost/lemora_dev")


def query(sql, params=None):
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        return conn.execute(sql, params).fetchall()