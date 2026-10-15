import pandas as pd
import logging

log = logging.getLogger(__name__)


def transform(df: pd.DataFrame, logical_date=None) -> pd.DataFrame:
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"]).dt.normalize()

    if logical_date is not None:
        df = df[df["Date"].dt.date == logical_date.date()]

    log.info("Số dòng sau transform: %d", len(df))
    log.info("logical_date=%s, min=%s, max=%s", logical_date.date(), df["Date"].min(), df["Date"].max())
    return df