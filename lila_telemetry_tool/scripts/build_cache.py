from pathlib import Path

from app.config import CACHE_DIR
from app.data_loader import load_raw_events, enrich_events, build_movement_segments


def main():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading raw telemetry...")
    raw_df = load_raw_events()
    print(f"Loaded rows: {len(raw_df)}")

    print("Enriching events...")
    events_df = enrich_events(raw_df)
    print(f"Enriched rows: {len(events_df)}")

    print("Building movement segments...")
    segments_df = build_movement_segments(events_df)
    print(f"Segments: {len(segments_df)}")

    events_path = CACHE_DIR / "events_master.parquet"
    segments_path = CACHE_DIR / "movement_segments.parquet"

    events_df.to_parquet(events_path, index=False)
    segments_df.to_parquet(segments_path, index=False)

    print(f"Saved: {events_path}")
    print(f"Saved: {segments_path}")
    print("Done.")


if __name__ == "__main__":
    main()