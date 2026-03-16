import re
from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq

from app.config import (
    PLAYER_DATA_DIR,
    MAP_CONFIG,
    MAP_SIZE_PX,
    BIN_PX,
    MOVEMENT_EVENTS,
    COMBAT_EVENTS,
    LOOT_EVENTS,
    STORM_EVENTS,
)

UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def classify_player_type(user_id: str) -> str:
    return "human" if UUID_RE.match(str(user_id)) else "bot"


def parse_source_date(path: Path) -> str:
    return path.parent.name


def decode_event(value):
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def world_to_pixel(map_id: str, x: float, z: float):
    cfg = MAP_CONFIG.get(map_id)
    if not cfg:
        return None, None, False

    u = (x - cfg["origin_x"]) / cfg["scale"]
    v = (z - cfg["origin_z"]) / cfg["scale"]

    px = u * MAP_SIZE_PX
    py = (1 - v) * MAP_SIZE_PX

    in_bounds = 0 <= px <= MAP_SIZE_PX and 0 <= py <= MAP_SIZE_PX
    return px, py, in_bounds


def kill_type_category(event: str) -> str | None:
    if event in {"Kill", "Killed"}:
        return "human_vs_human"
    if event == "BotKill":
        return "human_kills_bot"
    if event == "BotKilled":
        return "bot_kills_human"
    if event == "KilledByStorm":
        return "storm"
    return None


def load_raw_events() -> pd.DataFrame:
    frames = []
    files = sorted([p for p in PLAYER_DATA_DIR.rglob("*") if p.is_file() and p.name != "README.md"])

    for file_path in files:
        try:
            table = pq.read_table(file_path)
            df = table.to_pandas()
            if df.empty:
                continue

            df["event"] = df["event"].apply(decode_event)
            df["source_date"] = parse_source_date(file_path)
            df["source_file"] = file_path.name

            if "user_id" not in df.columns or "match_id" not in df.columns:
                continue

            df["user_id"] = df["user_id"].astype(str)
            df["match_id"] = df["match_id"].astype(str)
            df["player_type"] = df["user_id"].apply(classify_player_type)

            frames.append(df)
        except Exception as e:
            print(f"Skipping {file_path}: {e}")

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True)


def enrich_events(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()
    df = df[df["map_id"].isin(MAP_CONFIG.keys())].copy()

    df["ts"] = pd.to_datetime(df["ts"])
    df["ts_ms"] = (df["ts"].astype("int64") // 10**6).astype("int64")
    df["match_ts_ms"] = df.groupby("match_id")["ts_ms"].transform(lambda s: s - s.min())

    pixel_data = df.apply(lambda row: world_to_pixel(row["map_id"], row["x"], row["z"]), axis=1)
    df["pixel_x"] = [item[0] for item in pixel_data]
    df["pixel_y"] = [item[1] for item in pixel_data]
    df["in_bounds"] = [item[2] for item in pixel_data]

    df["pixel_x"] = df["pixel_x"].clip(0, MAP_SIZE_PX)
    df["pixel_y"] = df["pixel_y"].clip(0, MAP_SIZE_PX)

    df["bin_x"] = (df["pixel_x"] // BIN_PX).astype("int64")
    df["bin_y"] = (df["pixel_y"] // BIN_PX).astype("int64")

    df["is_movement"] = df["event"].isin(MOVEMENT_EVENTS)
    df["is_combat"] = df["event"].isin(COMBAT_EVENTS)
    df["is_loot"] = df["event"].isin(LOOT_EVENTS)
    df["is_storm"] = df["event"].isin(STORM_EVENTS)
    df["kill_type_category"] = df["event"].apply(kill_type_category)

    return df


def build_movement_segments(df: pd.DataFrame, sample_step: int = 8, min_mag: float = 8.0) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    movement = df[df["is_movement"]].copy()
    if movement.empty:
        return pd.DataFrame()

    movement = movement.sort_values(["match_id", "user_id", "match_ts_ms"])

    segments = []

    for (match_id, user_id), group in movement.groupby(["match_id", "user_id"]):
        group = group.reset_index(drop=True)

        if len(group) < sample_step + 1:
            continue

        for i in range(0, len(group) - sample_step, sample_step):
            a = group.iloc[i]
            b = group.iloc[i + sample_step]

            dx = b["pixel_x"] - a["pixel_x"]
            dy = b["pixel_y"] - a["pixel_y"]
            mag = (dx**2 + dy**2) ** 0.5

            if mag < min_mag:
                continue

            segments.append(
                {
                    "map_id": a["map_id"],
                    "source_date": a["source_date"],
                    "match_id": match_id,
                    "user_id": user_id,
                    "player_type": a["player_type"],
                    "bin_x": int(a["bin_x"]),
                    "bin_y": int(a["bin_y"]),
                    "dx": float(dx),
                    "dy": float(dy),
                    "magnitude": float(mag),
                }
            )

    return pd.DataFrame(segments)