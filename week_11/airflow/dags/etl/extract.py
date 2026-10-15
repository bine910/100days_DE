import pandas as pd
import logging


log = logging.getLogger(__name__)




def extract(file_path: str) -> pd.DataFrame:
    
    df = pd.read_csv(file_path, sep=";")
    log.info("Extracted %d rows from %s", len(df), file_path)
    return df