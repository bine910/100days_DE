import argparse
from datetime import date
from extract import extract, extract_from_minio
from transform import transform
from load import load

parser = argparse.ArgumentParser()
parser.add_argument("--start-date", default=None)
parser.add_argument("--end-date", default=None)
parser.add_argument("--source", default="local", choices=["local", "minio"])
args = parser.parse_args()

if args.source == "local":
    df = extract("../data/raw/XAU_1d_data.csv")
else:
    df = extract_from_minio("gold-price", "bronze/2026-09-22/XAU_1d_data.csv")

df = transform(df, args.start_date, args.end_date)
load(df)