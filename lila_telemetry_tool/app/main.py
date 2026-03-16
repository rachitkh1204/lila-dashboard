from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import MAP_CONFIG, MINIMAP_DIR
from app.analytics import (
    get_options,
    get_flow_overlay,
    get_combat_overlay,
    get_kill_type_overlay,
    get_loot_overlay,
    get_path_trace,
    get_timeline,
    get_match_players,
)

app = FastAPI(title="LILA Telemetry Visualization Tool")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "maps": list(MAP_CONFIG.keys())},
    )


@app.get("/api/options")
def options(
    map_id: str = "all",
    source_date: str = "all",
    match_id: str = "all",
    player_type: str = "all",
):
    return JSONResponse(get_options(map_id, source_date, match_id, player_type))


@app.get("/api/minimap/{map_id}")
def minimap(map_id: str):
    cfg = MAP_CONFIG.get(map_id)
    if not cfg:
        return JSONResponse({"error": "Unknown map"}, status_code=404)
    image_path = MINIMAP_DIR / cfg["image"]
    return FileResponse(image_path)


@app.get("/api/flow")
def flow(
    map_id: str = "AmbroseValley",
    source_date: str = "all",
    match_id: str = "all",
    player_type: str = "all",
):
    return JSONResponse(get_flow_overlay(map_id, source_date, match_id, player_type))


@app.get("/api/combat")
def combat(
    map_id: str = "AmbroseValley",
    source_date: str = "all",
    match_id: str = "all",
    player_type: str = "all",
    combat_type: str = "all",
):
    return JSONResponse(get_combat_overlay(map_id, source_date, match_id, player_type, combat_type))


@app.get("/api/kill-types")
def kill_types(
    map_id: str = "AmbroseValley",
    source_date: str = "all",
    match_id: str = "all",
    player_type: str = "all",
    kill_type: str = "all",
):
    return JSONResponse(get_kill_type_overlay(map_id, source_date, match_id, player_type, kill_type))


@app.get("/api/loot")
def loot(
    map_id: str = "AmbroseValley",
    source_date: str = "all",
    match_id: str = "all",
    player_type: str = "all",
):
    return JSONResponse(get_loot_overlay(map_id, source_date, match_id, player_type))


@app.get("/api/path")
def path_trace(
    map_id: str = "AmbroseValley",
    source_date: str = "all",
    match_id: str = "all",
    user_id: str = "all",
):
    return JSONResponse(get_path_trace(map_id, source_date, match_id, user_id))


@app.get("/api/timeline")
def timeline(
    map_id: str = "AmbroseValley",
    source_date: str = "all",
    match_id: str = "all",
    player_type: str = "all",
):
    return JSONResponse(get_timeline(map_id, source_date, match_id, player_type))


@app.get("/api/players")
def match_players(
    map_id: str = "AmbroseValley",
    source_date: str = "all",
    match_id: str = "all",
):
    return JSONResponse(get_match_players(map_id, source_date, match_id))