from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PLAYER_DATA_DIR = DATA_DIR / "player_data"
MINIMAP_DIR = DATA_DIR / "minimaps"
CACHE_DIR = BASE_DIR / "cache"

BIN_PX = 16
MAP_SIZE_PX = 1024

MAP_CONFIG = {
    "AmbroseValley": {
        "scale": 900,
        "origin_x": -370,
        "origin_z": -473,
        "image": "AmbroseValley_Minimap.png",
    },
    "GrandRift": {
        "scale": 581,
        "origin_x": -290,
        "origin_z": -290,
        "image": "GrandRift_Minimap.png",
    },
    "Lockdown": {
        "scale": 1000,
        "origin_x": -500,
        "origin_z": -500,
        "image": "Lockdown_Minimap.jpg",
    },
}

MOVEMENT_EVENTS = {"Position", "BotPosition"}
COMBAT_EVENTS = {"Kill", "Killed", "BotKill", "BotKilled"}
LOOT_EVENTS = {"Loot"}
STORM_EVENTS = {"KilledByStorm"}
ALL_SUPPORTED_EVENTS = MOVEMENT_EVENTS | COMBAT_EVENTS | LOOT_EVENTS | STORM_EVENTS