"""CLI entrypoint for real data collection pipeline.

Usage: python -m token_sentry.ml.collect
"""

import logging
import sys

from .data_collector import collect_all
from .data_processor import load_training_data, process_records, save_training_data

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    logger.info("Starting Token Sentry data collection pipeline")

    # Check for existing data (resume capability)
    existing = load_training_data()
    collected_addresses: set[str] = set()
    if existing is not None:
        collected_addresses = set(existing["address"].str.lower())
        logger.info("Found %d existing samples, will skip already-collected tokens", len(existing))

    # Collect from APIs
    logger.info("Collecting from GoPlusLabs + Basescan APIs...")
    records = collect_all()

    if not records:
        logger.warning("No records collected. Check API connectivity and rate limits.")
        if existing is not None:
            logger.info("Using existing %d samples", len(existing))
        else:
            logger.error("No data available. Exiting.")
            sys.exit(1)

    # Filter out already-collected addresses for resume capability
    new_records = [r for r in records if r["address"].lower() not in collected_addresses]
    logger.info("New records to process: %d (skipped %d existing)", len(new_records), len(records) - len(new_records))

    # Process new records
    new_df = process_records(new_records)

    # Merge with existing data
    if existing is not None and not new_df.empty:
        import pandas as pd
        combined = pd.concat([existing, new_df], ignore_index=True)
        # Deduplicate by address (keep latest)
        combined = combined.drop_duplicates(subset="address", keep="last")
    elif existing is not None:
        combined = existing
    else:
        combined = new_df

    if combined.empty:
        logger.error("No data to save. Exiting.")
        sys.exit(1)

    # Save
    path = save_training_data(combined)

    # Summary
    logger.info("=" * 60)
    logger.info("Collection complete!")
    logger.info("Total samples: %d", len(combined))
    logger.info("Saved to: %s", path)

    # Score distribution
    if "safety_score" in combined.columns:
        scores = combined["safety_score"]
        logger.info("Score distribution:")
        logger.info("  Safe (70-100):       %d", len(scores[scores >= 70]))
        logger.info("  Moderate (40-69):    %d", len(scores[(scores >= 40) & (scores < 70)]))
        logger.info("  Suspicious (20-39):  %d", len(scores[(scores >= 20) & (scores < 40)]))
        logger.info("  Dangerous (0-19):    %d", len(scores[scores < 20]))

    logger.info("=" * 60)
    logger.info("Next step: python -m token_sentry.ml.retrain")


if __name__ == "__main__":
    main()
