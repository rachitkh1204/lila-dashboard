from functools import lru_cache
import pandas as pd

from app.config import CACHE_DIR, BIN_PX, MAP_CONFIG


REPLAY_DURATION_SEC = 10.0

REPLAY_COLOR_PALETTE = [
    "#f97316",
    "#3b82f6",
    "#22c55e",
    "#eab308",
    "#a855f7",
    "#ef4444",
    "#14b8a6",
    "#ec4899",
    "#84cc16",
    "#f59e0b",
    "#06b6d4",
    "#8b5cf6",
    "#10b981",
    "#fb7185",
    "#60a5fa",
    "#facc15",
    "#34d399",
    "#c084fc",
    "#f87171",
    "#2dd4bf",
]


@lru_cache(maxsize=1)
def get_events_df() -> pd.DataFrame:
    path = CACHE_DIR / "events_master.parquet"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


@lru_cache(maxsize=1)
def get_segments_df() -> pd.DataFrame:
    path = CACHE_DIR / "movement_segments.parquet"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


def filter_df(df: pd.DataFrame, map_id=None, source_date=None, match_id=None, player_type=None):
    if df.empty:
        return df

    out = df.copy()

    if map_id and map_id != "all":
        out = out[out["map_id"] == map_id]
    if source_date and source_date != "all":
        out = out[out["source_date"] == source_date]
    if match_id and match_id != "all":
        out = out[out["match_id"] == match_id]
    if player_type and player_type != "all":
        out = out[out["player_type"] == player_type]

    return out


def get_options(map_id=None, source_date=None, match_id=None, player_type=None):
    df = get_events_df()
    if df.empty:
        return {
            "maps": list(MAP_CONFIG.keys()),
            "dates": [],
            "matches": [],
            "users": [],
        }

    filtered = filter_df(df, map_id=map_id, source_date=source_date, match_id=match_id, player_type=player_type)

    return {
        "maps": sorted(df["map_id"].dropna().astype(str).unique().tolist()),
        "dates": sorted(filter_df(df, map_id=map_id)["source_date"].dropna().astype(str).unique().tolist()),
        "matches": sorted(filter_df(df, map_id=map_id, source_date=source_date)["match_id"].dropna().astype(str).unique().tolist()),
        "users": sorted(filtered["user_id"].dropna().astype(str).unique().tolist()),
    }


def _build_flow_arrows_from_grouped(grouped: pd.DataFrame, min_count: int):
    grouped = grouped[grouped["count"] >= min_count].copy()
    if grouped.empty:
        return []

    max_count = grouped["count"].max()
    arrows = []

    for _, row in grouped.iterrows():
        cx = row["bin_x"] * BIN_PX + BIN_PX / 2
        cy = row["bin_y"] * BIN_PX + BIN_PX / 2

        norm = (row["avg_dx"] ** 2 + row["avg_dy"] ** 2) ** 0.5
        if norm == 0:
            continue

        ux = row["avg_dx"] / norm
        uy = row["avg_dy"] / norm

        length = 16 + 18 * (row["avg_mag"] / max(grouped["avg_mag"].max(), 1))
        length += 8 * (row["count"] / max_count)

        x2 = cx + ux * length
        y2 = cy + uy * length

        arrows.append(
            {
                "x1": round(cx, 2),
                "y1": round(cy, 2),
                "x2": round(x2, 2),
                "y2": round(y2, 2),
                "strength": int(row["count"]),
                "avg_mag": round(float(row["avg_mag"]), 2),
            }
        )

    return arrows


def get_flow_overlay(map_id=None, source_date=None, match_id=None, player_type=None):
    df = get_segments_df()
    df = filter_df(df, map_id, source_date, match_id, player_type)

    if df.empty:
        return {"arrows": [], "insights": "No movement data found for the current filters."}

    grouped = (
        df.groupby(["bin_x", "bin_y"], as_index=False)
        .agg(avg_dx=("dx", "mean"), avg_dy=("dy", "mean"), count=("dx", "size"), avg_mag=("magnitude", "mean"))
    )

    if not match_id or match_id == "all":
        arrows = _build_flow_arrows_from_grouped(grouped, min_count=3)
        if not arrows:
            return {"arrows": [], "insights": "Movement exists, but not enough density to form stable directional arrows."}

        top_bins = grouped[grouped["count"] >= 3].sort_values("count", ascending=False).head(3)
        max_count = int(grouped["count"].max())
        insight = (
            f"Movement clusters into {len(arrows)} meaningful bins. "
            f"Strongest corridor count is {max_count}. "
            f"Top active regions are around bins {top_bins[['bin_x', 'bin_y']].values.tolist()}."
        )
        return {"arrows": arrows, "insights": insight}

    per_match_grouped = (
        df.groupby(["bin_x", "bin_y"], as_index=False)
        .agg(avg_dx=("dx", "mean"), avg_dy=("dy", "mean"), count=("dx", "size"), avg_mag=("magnitude", "mean"))
    )

    arrows = _build_flow_arrows_from_grouped(per_match_grouped, min_count=1)

    if len(arrows) < 8:
        sparse = df.sort_values("magnitude", ascending=False).head(80).copy()
        sparse_arrows = []
        for _, row in sparse.iterrows():
            cx = row["bin_x"] * BIN_PX + BIN_PX / 2
            cy = row["bin_y"] * BIN_PX + BIN_PX / 2
            norm = (row["dx"] ** 2 + row["dy"] ** 2) ** 0.5
            if norm == 0:
                continue
            ux = row["dx"] / norm
            uy = row["dy"] / norm
            length = 14 + min(row["magnitude"], 32)
            sparse_arrows.append(
                {
                    "x1": round(cx, 2),
                    "y1": round(cy, 2),
                    "x2": round(cx + ux * length, 2),
                    "y2": round(cy + uy * length, 2),
                    "strength": 1,
                    "avg_mag": round(float(row["magnitude"]), 2),
                }
            )
        arrows = sparse_arrows

    if not arrows:
        return {"arrows": [], "insights": "No movement arrows could be constructed for this match."}

    busiest = per_match_grouped.sort_values(["avg_mag", "count"], ascending=False).head(3)
    insight = (
        f"Specific match mode is active, using a denser arrow strategy for sparse data. "
        f"Rendered {len(arrows)} arrows for this match. "
        f"Most active movement bins are around {busiest[['bin_x', 'bin_y']].values.tolist()}."
    )
    return {"arrows": arrows, "insights": insight}


def get_combat_overlay(map_id=None, source_date=None, match_id=None, player_type=None, combat_type="all"):
    df = get_events_df()
    df = filter_df(df, map_id, source_date, match_id, player_type)
    df = df[df["is_combat"]].copy()

    if combat_type != "all":
        df = df[df["event"] == combat_type]

    if df.empty:
        return {"cells": [], "markers": [], "insights": "No combat data found for the current filters."}

    cells = (
        df.groupby(["bin_x", "bin_y"], as_index=False)
        .size()
        .rename(columns={"size": "value"})
        .to_dict(orient="records")
    )

    markers_df = df.sample(min(len(df), 500), random_state=42) if len(df) > 500 else df
    markers = markers_df[["pixel_x", "pixel_y", "event"]].to_dict(orient="records")

    top_cells = sorted(cells, key=lambda x: x["value"], reverse=True)[:3]
    insight = f"Combat appears in {len(cells)} map cells. Hottest combat cell has {top_cells[0]['value']} events." if top_cells else "No combat hotspots detected."

    return {"cells": cells, "markers": markers, "insights": insight}


def get_kill_type_overlay(map_id=None, source_date=None, match_id=None, player_type=None, kill_type="all"):
    df = get_events_df()
    df = filter_df(df, map_id, source_date, match_id, player_type)
    df = df[df["kill_type_category"].notna()].copy()

    if kill_type != "all":
        df = df[df["kill_type_category"] == kill_type]

    if df.empty:
        return {"markers": [], "summary": {}, "insights": "No kill type data found for the current filters."}

    markers_df = df.sample(min(len(df), 500), random_state=42) if len(df) > 500 else df
    markers = markers_df[["pixel_x", "pixel_y", "kill_type_category"]].to_dict(orient="records")
    summary = df["kill_type_category"].value_counts().to_dict()

    top_type = max(summary, key=summary.get)
    insight = f"Most common kill interaction is '{top_type}' with {summary[top_type]} events."

    return {"markers": markers, "summary": summary, "insights": insight}


def get_loot_overlay(map_id=None, source_date=None, match_id=None, player_type=None):
    df = get_events_df()
    df = filter_df(df, map_id, source_date, match_id, player_type)
    df = df[df["is_loot"]].copy()

    if df.empty:
        return {"cells": [], "markers": [], "insights": "No loot data found for the current filters."}

    cells = (
        df.groupby(["bin_x", "bin_y"], as_index=False)
        .size()
        .rename(columns={"size": "value"})
        .to_dict(orient="records")
    )

    markers_df = df.sample(min(len(df), 500), random_state=42) if len(df) > 500 else df
    markers = markers_df[["pixel_x", "pixel_y"]].to_dict(orient="records")

    top_cells = sorted(cells, key=lambda x: x["value"], reverse=True)[:3]
    insight = f"Loot interactions cluster in {len(cells)} cells. Top loot zone has {top_cells[0]['value']} pickups." if top_cells else "No meaningful loot hotspots detected."

    return {"cells": cells, "markers": markers, "insights": insight}


def get_path_trace(map_id=None, source_date=None, match_id=None, user_id=None):
    df = get_events_df()
    df = filter_df(df, map_id, source_date, match_id, None)
    df = df[df["is_movement"]].copy()

    if user_id and user_id != "all":
        df = df[df["user_id"] == user_id]

    df = df.sort_values("match_ts_ms")

    if df.empty:
        return {"points": [], "insights": "No path data found. Select a match and a player."}

    points = df[["pixel_x", "pixel_y", "match_ts_ms"]].to_dict(orient="records")
    start = points[0]
    end = points[-1]

    insight = (
        f"Path contains {len(points)} sampled points. "
        f"Start near ({int(start['pixel_x'])}, {int(start['pixel_y'])}) "
        f"and ends near ({int(end['pixel_x'])}, {int(end['pixel_y'])})."
    )

    return {"points": points, "insights": insight}


def _short_id(value: str) -> str:
    value = str(value)
    if len(value) <= 12:
        return value
    return f"{value[:6]}...{value[-4:]}"


def _replay_event_kind(event_name: str) -> str | None:
    mapping = {
        "BotKill": "killed_bot",
        "BotKilled": "killed_by_bot",
        "Kill": "killed_human",
        "Killed": "killed_by_human",
        "KilledByStorm": "killed_by_storm",
        "Loot": "loot",
    }
    return mapping.get(event_name)


def _assign_participant_colors(user_ids: list[str]) -> dict[str, str]:
    colors = {}
    ordered = sorted([str(uid) for uid in user_ids])
    for idx, uid in enumerate(ordered):
        colors[uid] = REPLAY_COLOR_PALETTE[idx % len(REPLAY_COLOR_PALETTE)]
    return colors


def get_timeline(map_id=None, source_date=None, match_id=None, player_type=None):
    df = get_events_df()

    if not match_id or match_id == "all":
        return {
            "replay_duration_sec": REPLAY_DURATION_SEC,
            "min_t_ms": 0.0,
            "max_t_ms": 0.0,
            "elapsed_range_ms": 0.0,
            "normalization_multiplier": 0.0,
            "participants": [],
            "timeline_by_user": {},
            "events": [],
            "match_map_id": map_id,
            "insights": "Select a specific match to load the 10-second normalized replay.",
        }

    df = df[df["match_id"] == match_id].copy()

    if source_date and source_date != "all":
        df = df[df["source_date"] == source_date]

    if player_type and player_type != "all":
        df = df[df["player_type"] == player_type]

    if df.empty:
        return {
            "replay_duration_sec": REPLAY_DURATION_SEC,
            "min_t_ms": 0.0,
            "max_t_ms": 0.0,
            "elapsed_range_ms": 0.0,
            "normalization_multiplier": 0.0,
            "participants": [],
            "timeline_by_user": {},
            "events": [],
            "match_map_id": map_id,
            "insights": "No replay data found for the selected match and filters.",
        }

    match_map_id = str(df["map_id"].mode().iloc[0])

    ts_series = pd.to_datetime(df["ts"], utc=True, errors="coerce")
    df = df[ts_series.notna()].copy()
    df["ts_dt"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")

    if df.empty:
        return {
            "replay_duration_sec": REPLAY_DURATION_SEC,
            "min_t_ms": 0.0,
            "max_t_ms": 0.0,
            "elapsed_range_ms": 0.0,
            "normalization_multiplier": 0.0,
            "participants": [],
            "timeline_by_user": {},
            "events": [],
            "match_map_id": match_map_id,
            "insights": "Replay failed because no valid timestamp values were found.",
        }

    min_t = df["ts_dt"].min()
    max_t = df["ts_dt"].max()

    df["elapsed_t_ms"] = (df["ts_dt"] - min_t).dt.total_seconds() * 1000.0

    min_t_ms = 0.0
    max_t_ms = float(df["elapsed_t_ms"].max())
    elapsed_range_ms = max_t_ms - min_t_ms

    if elapsed_range_ms <= 0:
        elapsed_range_ms = 1.0

    normalization_multiplier = REPLAY_DURATION_SEC / elapsed_range_ms
    df["replay_time_sec"] = df["elapsed_t_ms"] * normalization_multiplier

    df = df.sort_values(["elapsed_t_ms", "user_id", "event"]).reset_index(drop=True)

    user_ids = sorted(df["user_id"].astype(str).unique().tolist())
    color_map = _assign_participant_colors(user_ids)

    timeline_by_user = {}
    participants = []

    for uid, group in df.groupby("user_id"):
        uid = str(uid)
        group = group.sort_values(["elapsed_t_ms", "event"]).copy()

        timeline = group[
            ["pixel_x", "pixel_y", "elapsed_t_ms", "replay_time_sec", "event", "player_type"]
        ].to_dict(orient="records")
        timeline_by_user[uid] = timeline

        last_row = group.iloc[-1]
        participants.append(
            {
                "user_id": uid,
                "short_id": _short_id(uid),
                "player_type": str(last_row["player_type"]),
                "color": color_map[uid],
                "last_replay_time_sec": float(last_row["replay_time_sec"]),
                "last_elapsed_t_ms": float(last_row["elapsed_t_ms"]),
                "final_x": round(float(last_row["pixel_x"]), 2),
                "final_y": round(float(last_row["pixel_y"]), 2),
                "last_event": str(last_row["event"]),
                "event_count": int(len(group)),
            }
        )

    replay_event_rows = df[df["event"].isin(["Kill", "Killed", "BotKill", "BotKilled", "KilledByStorm", "Loot"])].copy()
    replay_event_rows["event_kind"] = replay_event_rows["event"].apply(_replay_event_kind)
    replay_event_rows = replay_event_rows[replay_event_rows["event_kind"].notna()].sort_values(["elapsed_t_ms", "event"])

    replay_events = replay_event_rows[
        ["user_id", "player_type", "event", "event_kind", "pixel_x", "pixel_y", "elapsed_t_ms", "replay_time_sec"]
    ].copy()
    replay_events["user_id"] = replay_events["user_id"].astype(str)
    replay_events["short_id"] = replay_events["user_id"].apply(_short_id)
    replay_events = replay_events.to_dict(orient="records")

    longest_active = sorted(participants, key=lambda p: p["last_replay_time_sec"], reverse=True)[:3]
    first_combat = replay_event_rows[replay_event_rows["event"].isin(["Kill", "Killed", "BotKill", "BotKilled"])]
    first_loot = replay_event_rows[replay_event_rows["event"] == "Loot"]
    first_storm = replay_event_rows[replay_event_rows["event"] == "KilledByStorm"]

    insight_parts = [
        f"Replay uses elapsed time derived from ts - min(ts).",
        f"Match elapsed range is {elapsed_range_ms:.0f} ms and multiplier is {normalization_multiplier:.8f}.",
        f"Each event is placed at elapsed_t × (10 / elapsed_range).",
        f"Selected match contains {len(participants)} participants.",
    ]

    if longest_active:
        insight_parts.append(
            "Longest active participants: "
            + ", ".join([f"{p['short_id']} ({p['last_replay_time_sec']:.2f}s)" for p in longest_active])
            + "."
        )
    if not first_loot.empty:
        insight_parts.append(f"Loot begins around replay {first_loot['replay_time_sec'].min():.2f}s.")
    if not first_combat.empty:
        insight_parts.append(f"Combat begins around replay {first_combat['replay_time_sec'].min():.2f}s.")
    if not first_storm.empty:
        insight_parts.append(f"Storm deaths appear around replay {first_storm['replay_time_sec'].min():.2f}s.")

    return {
        "replay_duration_sec": REPLAY_DURATION_SEC,
        "min_t_ms": min_t_ms,
        "max_t_ms": max_t_ms,
        "elapsed_range_ms": elapsed_range_ms,
        "normalization_multiplier": normalization_multiplier,
        "participants": participants,
        "timeline_by_user": timeline_by_user,
        "events": replay_events,
        "match_map_id": match_map_id,
        "insights": " ".join(insight_parts),
    }


def get_match_players(map_id=None, source_date=None, match_id=None):
    df = get_events_df()
    df = filter_df(df, map_id, source_date, match_id, None)

    if match_id == "all" or not match_id:
        return {
            "players": [],
            "insights": "Select a specific match to see the player roster.",
        }

    if df.empty:
        return {
            "players": [],
            "insights": "No players found for the current filters.",
        }

    # Fix first seen / last seen using the same timestamp logic as replay:
    # elapsed time within selected match = ts - min(ts of that match)
    df["ts_dt"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")
    df = df[df["ts_dt"].notna()].copy()

    if df.empty:
        return {
            "players": [],
            "insights": "No valid timestamps found for the selected match.",
        }

    match_min_t = df["ts_dt"].min()
    df["elapsed_t_ms"] = (df["ts_dt"] - match_min_t).dt.total_seconds() * 1000.0

    grouped = (
        df.groupby(["user_id", "player_type"], as_index=False)
        .agg(
            event_count=("event", "size"),
            first_ts_ms=("elapsed_t_ms", "min"),
            last_ts_ms=("elapsed_t_ms", "max"),
        )
        .sort_values(["player_type", "event_count", "user_id"], ascending=[True, False, True])
    )

    players = grouped.to_dict(orient="records")
    player_counts = grouped["player_type"].value_counts().to_dict()
    humans = player_counts.get("human", 0)
    bots = player_counts.get("bot", 0)

    insight = (
        f"Roster for selected match contains {len(players)} participants: "
        f"{humans} humans and {bots} bots."
    )

    return {"players": players, "insights": insight}