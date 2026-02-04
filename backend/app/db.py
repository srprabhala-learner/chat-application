import psycopg
from psycopg.rows import dict_row

from app.config import settings


def get_conn():
    return psycopg.connect(
        host=settings.pg_host,
        port=settings.pg_port,
        dbname=settings.pg_db,
        user=settings.pg_user,
        password=settings.pg_password,
        row_factory=dict_row,
    )


