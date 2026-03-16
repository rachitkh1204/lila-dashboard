const state = {
  mode: "flow",
  mapId: "AmbroseValley",
  sourceDate: "all",
  matchId: "all",
  playerType: "all",
  userId: "all",
  combatType: "all",
  killType: "all",
  timelineTimer: null,
  replayData: null,
  replayClockSec: 0,
  replayTickMs: 50,
};

const overlay = document.getElementById("overlay");
const minimap = document.getElementById("minimap");
const insightsEl = document.getElementById("insights");
const legendEl = document.getElementById("legend");

const dateSelect = document.getElementById("dateSelect");
const matchSelect = document.getElementById("matchSelect");
const playerTypeSelect = document.getElementById("playerTypeSelect");
const userSelect = document.getElementById("userSelect");
const combatTypeSelect = document.getElementById("combatTypeSelect");
const killTypeSelect = document.getElementById("killTypeSelect");

const pathUserWrap = document.getElementById("pathUserWrap");
const combatTypeWrap = document.getElementById("combatTypeWrap");
const killTypeWrap = document.getElementById("killTypeWrap");
const playerTypeWrap = document.getElementById("playerTypeWrap");
const timelineControls = document.getElementById("timelineControls");
const mapStage = document.getElementById("mapStage");
const playersPanel = document.getElementById("playersPanel");
const playersList = document.getElementById("playersList");
const playersCount = document.getElementById("playersCount");

const timelineSlider = document.getElementById("timelineSlider");
const timelineLabel = document.getElementById("timelineLabel");

const COMBAT_HEATMAP_ALPHA_MULTIPLIER = 2.5;

const PATH_ARROW_SPACING = 28;
const PATH_ARROW_HEAD_SIZE = 8;
const PATH_LINE_WIDTH = 3;

const REPLAY_PLAYER_ICON_SCALE = 1.15;
const REPLAY_EVENT_FADE_SEC = 0.9;
const REPLAY_MAX_SEC = 10.0;

function setMode(mode) {
  state.mode = mode;

  document.querySelectorAll(".mode-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.mode === mode);
  });

  pathUserWrap.classList.toggle("hidden", mode !== "path");
  combatTypeWrap.classList.toggle("hidden", mode !== "combat");
  killTypeWrap.classList.toggle("hidden", mode !== "kill-types");
  timelineControls.classList.toggle("hidden", mode !== "timeline");
  playersPanel.classList.toggle("hidden", mode !== "players");
  mapStage.classList.toggle("hidden", mode === "players");

  playerTypeWrap.classList.toggle("hidden", mode === "players");

  renderLegend();
  refreshDependentFilters().then(loadCurrentView);
}

function buildLegend(items) {
  legendEl.innerHTML = "";
  items.forEach(item => {
    const row = document.createElement("div");
    row.className = "legend-item";
    row.innerHTML = `
      <div class="legend-swatch" style="background:${item.color}"></div>
      <div>${item.label}</div>
    `;
    legendEl.appendChild(row);
  });
}

function renderLegend() {
  if (state.mode === "flow") {
    buildLegend([{ color: "#f97316", label: "Movement arrows" }]);
  } else if (state.mode === "combat") {
    buildLegend([
      { color: "#facc15", label: "Kill / Killed" },
      { color: "#a855f7", label: "BotKill" },
      { color: "#22c55e", label: "BotKilled" },
      { color: "#ef4444", label: "Combat density" },
    ]);
  } else if (state.mode === "kill-types") {
    buildLegend([
      { color: "#facc15", label: "human_vs_human" },
      { color: "#a855f7", label: "human_kills_bot" },
      { color: "#22c55e", label: "bot_kills_human" },
      { color: "#3b82f6", label: "storm" },
    ]);
  } else if (state.mode === "loot") {
    buildLegend([
      { color: "#22c55e", label: "Loot markers" },
      { color: "#10b981", label: "Loot hotspot cells" },
    ]);
  } else if (state.mode === "path") {
    buildLegend([
      { color: "#f97316", label: "Path line" },
      { color: "#fdba74", label: "Direction arrows" },
      { color: "#22c55e", label: "Start" },
      { color: "#ef4444", label: "End" },
    ]);
  } else if (state.mode === "timeline") {
    renderReplayLegend(state.replayData);
  } else if (state.mode === "players") {
    buildLegend([
      { color: "#fb923c", label: "Human player" },
      { color: "#60a5fa", label: "Bot" },
    ]);
  }
}

function renderReplayLegend(replayData) {
  const participants = replayData?.participants || [];
  const eventItems = [
    { color: "#a855f7", label: "Killed a Bot" },
    { color: "#22c55e", label: "Killed by Bot" },
    { color: "#facc15", label: "Killed a Human" },
    { color: "#f97316", label: "Killed by Human" },
    { color: "#3b82f6", label: "Killed by Storm" },
    { color: "#10b981", label: "Loot Interaction" },
  ];

  legendEl.innerHTML = "";

  const eventTitle = document.createElement("div");
  eventTitle.style.marginBottom = "8px";
  eventTitle.style.fontWeight = "600";
  eventTitle.textContent = "Replay Events";
  legendEl.appendChild(eventTitle);

  eventItems.forEach(item => {
    const row = document.createElement("div");
    row.className = "legend-item";
    row.innerHTML = `
      <div class="legend-swatch" style="background:${item.color}"></div>
      <div>${item.label}</div>
    `;
    legendEl.appendChild(row);
  });

  const divider = document.createElement("div");
  divider.style.height = "1px";
  divider.style.background = "#2b3440";
  divider.style.margin = "14px 0";
  legendEl.appendChild(divider);

  const playerTitle = document.createElement("div");
  playerTitle.style.marginBottom = "8px";
  playerTitle.style.fontWeight = "600";
  playerTitle.textContent = "Players";
  legendEl.appendChild(playerTitle);

  if (!participants.length) {
    const empty = document.createElement("div");
    empty.className = "muted";
    empty.textContent = "Select a match to load player colors.";
    legendEl.appendChild(empty);
    return;
  }

  participants.forEach(p => {
    const row = document.createElement("div");
    row.className = "legend-item";
    row.style.alignItems = "flex-start";
    row.innerHTML = `
      <div class="legend-swatch" style="background:${p.color}; margin-top:3px;"></div>
      <div>
        <div>${p.short_id}</div>
        <div style="font-size:12px; color:#98a2b3;">${p.player_type}</div>
      </div>
    `;
    legendEl.appendChild(row);
  });
}

function eventColor(event) {
  if (event === "Kill" || event === "Killed") return "#facc15";
  if (event === "BotKill") return "#a855f7";
  if (event === "BotKilled") return "#22c55e";
  if (event === "KilledByStorm") return "#3b82f6";
  if (event === "Loot") return "#22c55e";
  return "#94a3b8";
}

function killTypeColor(type) {
  if (type === "human_vs_human") return "#facc15";
  if (type === "human_kills_bot") return "#a855f7";
  if (type === "bot_kills_human") return "#22c55e";
  if (type === "storm") return "#3b82f6";
  return "#94a3b8";
}

function replayEventColor(kind) {
  if (kind === "killed_bot") return "#a855f7";
  if (kind === "killed_by_bot") return "#22c55e";
  if (kind === "killed_human") return "#facc15";
  if (kind === "killed_by_human") return "#f97316";
  if (kind === "killed_by_storm") return "#3b82f6";
  if (kind === "loot") return "#10b981";
  return "#94a3b8";
}

function clearOverlay() {
  overlay.innerHTML = "";
}

function addSvg(tag, attrs) {
  const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
  Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
  overlay.appendChild(el);
  return el;
}

function addSvgTo(parent, tag, attrs) {
  const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
  Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
  parent.appendChild(el);
  return el;
}

function drawHeatCells(cells, baseColor = "#ef4444", alphaMultiplier = 1) {
  if (!cells.length) return;
  const max = Math.max(...cells.map(c => c.value));
  cells.forEach(cell => {
    const normalized = cell.value / max;
    const alpha = Math.min(0.95, Math.max(0.18, normalized * alphaMultiplier));
    addSvg("rect", {
      x: cell.bin_x * 16,
      y: cell.bin_y * 16,
      width: 16,
      height: 16,
      fill: baseColor,
      "fill-opacity": alpha,
      stroke: "none",
    });
  });
}

function drawCombatMarkers(markers) {
  markers.forEach(m => {
    addSvg("circle", {
      cx: m.pixel_x,
      cy: m.pixel_y,
      r: 3,
      fill: eventColor(m.event),
      opacity: 0.95,
    });
  });
}

function drawKillTypeMarkers(markers) {
  markers.forEach(m => {
    addSvg("circle", {
      cx: m.pixel_x,
      cy: m.pixel_y,
      r: 3,
      fill: killTypeColor(m.kill_type_category),
      opacity: 0.9,
    });
  });
}

function drawLootMarkers(markers) {
  markers.forEach(m => {
    addSvg("circle", {
      cx: m.pixel_x,
      cy: m.pixel_y,
      r: 3,
      fill: "#22c55e",
      opacity: 0.9,
    });
  });
}

function drawFlow(arrows) {
  if (!arrows.length) return;
  const max = Math.max(...arrows.map(a => a.strength));

  arrows.forEach(a => {
    const w = 1.6 + (a.strength / max) * 3.2;
    addSvg("line", {
      x1: a.x1,
      y1: a.y1,
      x2: a.x2,
      y2: a.y2,
      stroke: "#f97316",
      "stroke-width": w,
      "stroke-linecap": "round",
      opacity: 0.92,
    });

    const angle = Math.atan2(a.y2 - a.y1, a.x2 - a.x1);
    const head = 8;
    const x3 = a.x2 - head * Math.cos(angle - Math.PI / 6);
    const y3 = a.y2 - head * Math.sin(angle - Math.PI / 6);
    const x4 = a.x2 - head * Math.cos(angle + Math.PI / 6);
    const y4 = a.y2 - head * Math.sin(angle + Math.PI / 6);

    addSvg("polygon", {
      points: `${a.x2},${a.y2} ${x3},${y3} ${x4},${y4}`,
      fill: "#f97316",
      opacity: 0.92,
    });
  });
}

function drawArrowHead(x, y, angle, color = "#fdba74", size = PATH_ARROW_HEAD_SIZE) {
  const x2 = x - size * Math.cos(angle - Math.PI / 6);
  const y2 = y - size * Math.sin(angle - Math.PI / 6);
  const x3 = x - size * Math.cos(angle + Math.PI / 6);
  const y3 = y - size * Math.sin(angle + Math.PI / 6);

  addSvg("polygon", {
    points: `${x},${y} ${x2},${y2} ${x3},${y3}`,
    fill: color,
    opacity: 0.95,
  });
}

function drawPath(points) {
  if (!points.length) return;

  const poly = points.map(p => `${p.pixel_x},${p.pixel_y}`).join(" ");
  addSvg("polyline", {
    points: poly,
    fill: "none",
    stroke: "#f97316",
    "stroke-width": PATH_LINE_WIDTH,
    opacity: 0.9,
    "stroke-linecap": "round",
    "stroke-linejoin": "round",
  });

  for (let i = 1; i < points.length; i++) {
    const x1 = points[i - 1].pixel_x;
    const y1 = points[i - 1].pixel_y;
    const x2 = points[i].pixel_x;
    const y2 = points[i].pixel_y;

    const dx = x2 - x1;
    const dy = y2 - y1;
    const segLen = Math.sqrt(dx * dx + dy * dy);

    if (segLen < 10) continue;

    const angle = Math.atan2(dy, dx);
    const arrowCount = Math.max(1, Math.floor(segLen / PATH_ARROW_SPACING));

    for (let j = 1; j <= arrowCount; j++) {
      const t = j / (arrowCount + 1);
      const ax = x1 + dx * t;
      const ay = y1 + dy * t;
      drawArrowHead(ax, ay, angle);
    }
  }

  addSvg("circle", { cx: points[0].pixel_x, cy: points[0].pixel_y, r: 6, fill: "#22c55e" });
  addSvg("circle", { cx: points[points.length - 1].pixel_x, cy: points[points.length - 1].pixel_y, r: 6, fill: "#ef4444" });
}

function getParticipantPositionAtTime(timeline, clockSec) {
  if (!timeline || !timeline.length) return null;

  let latest = null;
  for (const row of timeline) {
    if (row.replay_time_sec <= clockSec) {
      latest = row;
    } else {
      break;
    }
  }
  return latest;
}

function drawReplayParticipant(participant, position, isInactive) {
  const g = addSvg("g", {
    transform: `translate(${position.pixel_x}, ${position.pixel_y}) scale(${REPLAY_PLAYER_ICON_SCALE})`,
    opacity: isInactive ? 0.55 : 1.0,
  });

  addSvgTo(g, "path", {
    d: "M 0 -13 C -7 -13 -11 -8 -11 -2 C -11 7 0 16 0 16 C 0 16 11 7 11 -2 C 11 -8 7 -13 0 -13 Z",
    fill: participant.color,
    stroke: "#ffffff",
    "stroke-width": 1.5,
  });

  addSvgTo(g, "circle", {
    cx: 0,
    cy: -3,
    r: 4.2,
    fill: "#ffffff",
    opacity: 0.95,
  });

  addSvgTo(g, "circle", {
    cx: 0,
    cy: -3,
    r: 2.3,
    fill: participant.color,
  });
}

function drawReplayEventAnimation(ev, clockSec) {
  const age = clockSec - ev.replay_time_sec;
  if (age < 0 || age > REPLAY_EVENT_FADE_SEC) return;

  const fade = 1 - age / REPLAY_EVENT_FADE_SEC;
  const color = replayEventColor(ev.event_kind);
  const g = addSvg("g", {
    transform: `translate(${ev.pixel_x}, ${ev.pixel_y})`,
    opacity: Math.max(0.08, fade),
  });

  if (ev.event_kind === "loot") {
    addSvgTo(g, "circle", {
      cx: 0,
      cy: 0,
      r: 5 + age * 10,
      fill: "none",
      stroke: color,
      "stroke-width": 2,
    });
    addSvgTo(g, "polygon", {
      points: "0,-7 3,-2 8,0 3,2 0,7 -3,2 -8,0 -3,-2",
      fill: color,
    });
    return;
  }

  if (ev.event_kind === "killed_by_storm") {
    addSvgTo(g, "circle", {
      cx: 0,
      cy: 0,
      r: 7 + age * 12,
      fill: "none",
      stroke: color,
      "stroke-width": 2.5,
    });
    addSvgTo(g, "line", {
      x1: -8,
      y1: 8,
      x2: 8,
      y2: -8,
      stroke: color,
      "stroke-width": 2.5,
      "stroke-linecap": "round",
    });
    return;
  }

  if (ev.event_kind === "killed_by_bot" || ev.event_kind === "killed_by_human") {
    addSvgTo(g, "line", {
      x1: -8,
      y1: -8,
      x2: 8,
      y2: 8,
      stroke: color,
      "stroke-width": 3,
      "stroke-linecap": "round",
    });
    addSvgTo(g, "line", {
      x1: 8,
      y1: -8,
      x2: -8,
      y2: 8,
      stroke: color,
      "stroke-width": 3,
      "stroke-linecap": "round",
    });
    addSvgTo(g, "circle", {
      cx: 0,
      cy: 0,
      r: 10 + age * 8,
      fill: "none",
      stroke: color,
      "stroke-width": 1.5,
      opacity: 0.7,
    });
    return;
  }

  addSvgTo(g, "circle", {
    cx: 0,
    cy: 0,
    r: 4,
    fill: color,
  });

  for (let i = 0; i < 8; i++) {
    const angle = (Math.PI * 2 * i) / 8;
    const inner = 6;
    const outer = 12 + age * 10;
    addSvgTo(g, "line", {
      x1: Math.cos(angle) * inner,
      y1: Math.sin(angle) * inner,
      x2: Math.cos(angle) * outer,
      y2: Math.sin(angle) * outer,
      stroke: color,
      "stroke-width": 2,
      "stroke-linecap": "round",
    });
  }
}

function drawReplayFrame(clockSec) {
  clearOverlay();

  const replayData = state.replayData;
  if (!replayData) return;

  const participants = replayData.participants || [];
  const timelineByUser = replayData.timeline_by_user || {};
  const events = replayData.events || [];

  for (const participant of participants) {
    const timeline = timelineByUser[participant.user_id] || [];
    const position = getParticipantPositionAtTime(timeline, clockSec);
    if (!position) continue;

    const isInactive = clockSec > participant.last_replay_time_sec;
    drawReplayParticipant(participant, position, isInactive);
  }

  for (const ev of events) {
    drawReplayEventAnimation(ev, clockSec);
  }

  timelineLabel.textContent = `${clockSec.toFixed(2)}s / 10.00s`;
}

function stopReplayTimer() {
  if (state.timelineTimer) {
    clearInterval(state.timelineTimer);
    state.timelineTimer = null;
  }
}

function playReplay() {
  if (!state.replayData || !state.replayData.participants?.length) return;

  stopReplayTimer();

  state.timelineTimer = setInterval(() => {
    const next = Math.min(REPLAY_MAX_SEC, state.replayClockSec + state.replayTickMs / 1000);
    state.replayClockSec = next;
    timelineSlider.value = next.toFixed(2);
    drawReplayFrame(next);

    if (next >= REPLAY_MAX_SEC) {
      stopReplayTimer();
    }
  }, state.replayTickMs);
}

function renderPlayers(players) {
  playersList.innerHTML = "";

  const header = document.createElement("div");
  header.className = "player-row header";
  header.innerHTML = `
    <div>Type</div>
    <div>Player ID</div>
    <div>Events</div>
    <div>First Seen</div>
    <div>Last Seen</div>
  `;
  playersList.appendChild(header);

  players.forEach(player => {
    const row = document.createElement("div");
    row.className = "player-row";
    row.innerHTML = `
      <div><span class="player-pill ${player.player_type}">${player.player_type}</span></div>
      <div class="player-id">${player.user_id}</div>
      <div>${player.event_count}</div>
      <div>${(player.first_ts_ms / 1000).toFixed(1)}s</div>
      <div>${(player.last_ts_ms / 1000).toFixed(1)}s</div>
    `;
    playersList.appendChild(row);
  });

  playersCount.textContent = `${players.length} players`;
}

async function fetchJSON(url) {
  const res = await fetch(url);
  return res.json();
}

function setSelectOptions(selectEl, values, selectedValue, includeAll = true) {
  const current = selectedValue ?? "all";
  selectEl.innerHTML = "";

  if (includeAll) {
    const allOption = document.createElement("option");
    allOption.value = "all";
    allOption.textContent = "All";
    selectEl.appendChild(allOption);
  }

  values.forEach(value => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    selectEl.appendChild(option);
  });

  const exists = [...selectEl.options].some(opt => opt.value === current);
  selectEl.value = exists ? current : (includeAll ? "all" : (values[0] || ""));
}

function buildBaseQuery() {
  return new URLSearchParams({
    map_id: state.mapId,
    source_date: state.sourceDate,
    match_id: state.matchId,
    player_type: state.playerType,
  });
}

function buildQuery(extra = {}) {
  const params = buildBaseQuery();
  Object.entries(extra).forEach(([k, v]) => params.set(k, v));
  return params.toString();
}

function buildMapTabs(maps) {
  const wrap = document.getElementById("mapTabs");
  wrap.innerHTML = "";

  maps.forEach(map => {
    const btn = document.createElement("button");
    btn.className = `map-tab ${map === state.mapId ? "active" : ""}`;
    btn.textContent = map;
    btn.onclick = async () => {
      state.mapId = map;
      state.sourceDate = "all";
      state.matchId = "all";
      state.userId = "all";
      buildMapTabs(maps);
      await refreshDependentFilters();
      loadCurrentView();
    };
    wrap.appendChild(btn);
  });
}

async function refreshDependentFilters() {
  const basePlayerType = state.mode === "players" ? "all" : state.playerType;

  const options = await fetchJSON(`/api/options?${new URLSearchParams({
    map_id: state.mapId,
    source_date: state.sourceDate,
    match_id: state.matchId,
    player_type: basePlayerType,
  }).toString()}`);

  buildMapTabs(options.maps || ["AmbroseValley", "GrandRift", "Lockdown"]);

  setSelectOptions(dateSelect, options.dates || [], state.sourceDate, true);
  state.sourceDate = dateSelect.value;

  const matchOptions = await fetchJSON(
    `/api/options?${new URLSearchParams({
      map_id: state.mapId,
      source_date: state.sourceDate,
      match_id: "all",
      player_type: basePlayerType,
    }).toString()}`
  );

  setSelectOptions(matchSelect, matchOptions.matches || [], state.matchId, true);
  state.matchId = matchSelect.value;

  const userOptions = await fetchJSON(
    `/api/options?${new URLSearchParams({
      map_id: state.mapId,
      source_date: state.sourceDate,
      match_id: state.matchId,
      player_type: state.playerType,
    }).toString()}`
  );

  setSelectOptions(userSelect, userOptions.users || [], state.userId, true);
  state.userId = userSelect.value;

  playerTypeSelect.value = state.playerType;
  combatTypeSelect.value = state.combatType;
  killTypeSelect.value = state.killType;
}

async function loadCurrentView() {
  stopReplayTimer();
  clearOverlay();

  let data;

  if (state.mode === "flow") {
    minimap.src = `/api/minimap/${state.mapId}`;
    data = await fetchJSON(`/api/flow?${buildQuery()}`);
    drawFlow(data.arrows || []);
  }

  if (state.mode === "combat") {
    minimap.src = `/api/minimap/${state.mapId}`;
    data = await fetchJSON(`/api/combat?${buildQuery({ combat_type: state.combatType })}`);
    drawHeatCells(data.cells || [], "#ef4444", COMBAT_HEATMAP_ALPHA_MULTIPLIER);
    drawCombatMarkers(data.markers || []);
  }

  if (state.mode === "kill-types") {
    minimap.src = `/api/minimap/${state.mapId}`;
    data = await fetchJSON(`/api/kill-types?${buildQuery({ kill_type: state.killType })}`);
    drawKillTypeMarkers(data.markers || []);
  }

  if (state.mode === "loot") {
    minimap.src = `/api/minimap/${state.mapId}`;
    data = await fetchJSON(`/api/loot?${buildQuery()}`);
    drawHeatCells(data.cells || [], "#10b981", 1.2);
    drawLootMarkers(data.markers || []);
  }

  if (state.mode === "path") {
    minimap.src = `/api/minimap/${state.mapId}`;
    data = await fetchJSON(`/api/path?${buildQuery({ user_id: state.userId })}`);
    drawPath(data.points || []);
  }

  if (state.mode === "timeline") {
    data = await fetchJSON(`/api/timeline?${buildQuery()}`);
    state.replayData = data;

    if (data.match_map_id) {
      state.mapId = data.match_map_id;
      buildMapTabs(["AmbroseValley", "GrandRift", "Lockdown"]);
    }

    minimap.src = `/api/minimap/${state.mapId}`;

    timelineSlider.min = 0;
    timelineSlider.max = REPLAY_MAX_SEC;
    timelineSlider.step = 0.01;
    state.replayClockSec = 0;
    timelineSlider.value = 0;

    drawReplayFrame(0);
    renderReplayLegend(data);
  }

  if (state.mode === "players") {
    data = await fetchJSON(`/api/players?${new URLSearchParams({
      map_id: state.mapId,
      source_date: state.sourceDate,
      match_id: state.matchId,
    }).toString()}`);
    renderPlayers(data.players || []);
  }

  insightsEl.textContent = data?.insights || "No insight available.";
}

async function handleAutoApply(changes = {}) {
  Object.assign(state, changes);
  await refreshDependentFilters();
  await loadCurrentView();
}

document.querySelectorAll(".mode-btn").forEach(btn => {
  btn.addEventListener("click", () => setMode(btn.dataset.mode));
});

dateSelect.addEventListener("change", async (e) => {
  state.sourceDate = e.target.value;
  state.matchId = "all";
  state.userId = "all";
  await handleAutoApply();
});

matchSelect.addEventListener("change", async (e) => {
  state.matchId = e.target.value;
  state.userId = "all";
  await handleAutoApply();
});

playerTypeSelect.addEventListener("change", async (e) => {
  state.playerType = e.target.value;
  state.userId = "all";
  await handleAutoApply();
});

userSelect.addEventListener("change", async (e) => {
  state.userId = e.target.value;
  await handleAutoApply();
});

combatTypeSelect.addEventListener("change", async (e) => {
  state.combatType = e.target.value;
  await handleAutoApply();
});

killTypeSelect.addEventListener("change", async (e) => {
  state.killType = e.target.value;
  await handleAutoApply();
});

timelineSlider.addEventListener("input", (e) => {
  if (state.mode !== "timeline") return;
  stopReplayTimer();
  state.replayClockSec = Number(e.target.value);
  drawReplayFrame(state.replayClockSec);
});

document.getElementById("playBtn").addEventListener("click", () => {
  if (state.mode !== "timeline") return;
  playReplay();
});

document.getElementById("pauseBtn").addEventListener("click", () => {
  stopReplayTimer();
});

document.getElementById("restartBtn").addEventListener("click", () => {
  if (state.mode !== "timeline") return;
  stopReplayTimer();
  state.replayClockSec = 0;
  timelineSlider.value = 0;
  drawReplayFrame(0);
});

window.addEventListener("load", async () => {
  renderLegend();
  await refreshDependentFilters();
  await loadCurrentView();
});