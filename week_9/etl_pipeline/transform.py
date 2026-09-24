import pandas as pd
from extract import extract
from datetime import date
from logger import log
import boto3

def transform(df: pd.DataFrame,begin_date: str, end_date: str) -> pd.DataFrame:
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"])
    if begin_date and end_date:
        df = df[
        (df["Date"] >= pd.to_datetime(begin_date)) &
        (df["Date"] <= pd.to_datetime(end_date))]
    log.info(f"số dòng sau khi transform: {len(df)}")
    return df

