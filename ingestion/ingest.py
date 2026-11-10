"""Ingest and preprocess the Zomato restaurant dataset from Hugging Face."""
import os
import sys
import logging
import pandas as pd
from ingestion.cleaner import clean_rating, clean_cost, clean_votes

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

HF_PARQUET_URLS = [
    "https://huggingface.co/api/datasets/ManikaSaini/zomato-restaurant-recommendation/parquet/default/train/0.parquet",
    "https://huggingface.co/api/datasets/ManikaSaini/zomato-restaurant-recommendation/parquet/default/train/1.parquet",
]
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
OUTPUT_CSV = os.path.join(DATA_DIR, "restaurants.csv")


def download_and_preprocess():
    """
    Download dataset splits from Hugging Face, clean required columns, and save to data/restaurants.csv.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    cols = [
        "name", "location", "cuisines", "rate", "votes",
        "approx_cost(for two people)", "online_order", "book_table", "rest_type", "address"
    ]

    dfs = []
    for url in HF_PARQUET_URLS:
        logger.info("Downloading and reading %s ...", url)
        df_part = pd.read_parquet(url, columns=cols)
        dfs.append(df_part)
        logger.info("Loaded %d rows from split", len(df_part))

    df_raw = pd.concat(dfs, ignore_index=True)
    logger.info("Total raw rows loaded: %d", len(df_raw))

    cleaned_records = []
    for idx, row in df_raw.iterrows():
        name = str(row["name"]).strip() if pd.notna(row.get("name")) else ""
        location = str(row["location"]).strip() if pd.notna(row.get("location")) else ""
        cuisine = str(row["cuisines"]).strip() if pd.notna(row.get("cuisines")) else ""
        cost = clean_cost(row.get("approx_cost(for two people)"))
        rating = clean_rating(str(row.get("rate")))
        if not name or not location or not cuisine or cost is None or rating is None:
            continue

        cleaned_records.append({
            "id": f"zom_{idx+1}",
            "name": name,
            "location": location,
            "cuisine": cuisine,
            "cost": cost,
            "rating": rating,
            "votes": clean_votes(row.get("votes")),
            "online_order": str(row.get("online_order", "")).strip(),
            "table_booking": str(row.get("book_table", "")).strip(),
            "rest_type": str(row.get("rest_type", "")).strip(),
            "address": str(row.get("address", "")).strip(),
        })

    df_clean = pd.DataFrame(cleaned_records)
    # Deduplicate by name and location
    df_clean.drop_duplicates(subset=["name", "location"], inplace=True)
    df_clean.to_csv(OUTPUT_CSV, index=False)
    logger.info("Successfully saved %d cleaned restaurants to %s", len(df_clean), OUTPUT_CSV)
    return len(df_clean)


if __name__ == "__main__":
    download_and_preprocess()
