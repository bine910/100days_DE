import pandas as pd
import logging
from airflow.providers.postgres.hooks.postgres import PostgresHook

log = logging.getLogger(__name__)
COLUMNS = ["Date", "Open", "High", "Low", "Close", "Volume"]
INSERT_SQL = """
    INSERT INTO gold_price_daily (date, open, high, low, close, volume)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (date) DO UPDATE SET
        open   = EXCLUDED.open,
        high   = EXCLUDED.high,
        low    = EXCLUDED.low,
        close  = EXCLUDED.close,
        volume = EXCLUDED.volume
"""

def load(df: pd.DataFrame) -> int:
    if df.empty:
        log.warning("DataFrame rỗng — không có gì để load")
        return 0

    rows = list(df[COLUMNS].itertuples(index=False, name=None))

    hook = PostgresHook(postgres_conn_id="postgres_dwh")
    with hook.get_conn() as conn:
        log.info("conn type: %s", type(conn))
        with conn.cursor() as cursor:
            cursor.executemany(INSERT_SQL, rows)
        conn.commit()

    log.info("Loaded %d rows into gold_price_daily", len(rows))
    return len(rows)
    
