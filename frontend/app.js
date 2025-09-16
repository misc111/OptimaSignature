const STATE_URL = "/state";
const SPEED_URL = "/speed";
const MANIFEST_URL = "app.manifest.json";
const UPDATE_INTERVAL = 1200;
const ELEVATOR_X = 0.5;
const WALK_FRAME_MS = 160;
const IDLE_FRAME_MS = 720;
const LAYER_ORDER = { background: 0, mid: 1, foreground: 2 };
const DEFAULT_ACTIVITY_ANCHOR = { x: 0.5, y: 0.92 };

const canvas = document.getElementById("twinCanvas");
const ctx = canvas.getContext("2d");
const clockEl = document.getElementById("clock");
const daylightEl = document.getElementById("daylight");
const activityList = document.getElementById("activityStats");
const amenityList = document.getElementById("amenityStats");
const residentList = document.getElementById("residentSpotlight");
const eventList = document.getElementById("eventFeed");
const speedButtons = Array.from(document.querySelectorAll(".speed"));

let spriteLibrary = null;
let manifest = null;
let assetsReady = false;
let building = null;
let roomLookup = new Map();
let cachedRoomGeometry = { key: "", rooms: [] };

let currentState = null;
let previousState = null;
let previousMap = new Map();
let lastUpdateTime = 0;
let currentSpeed = "normal";

function resizeCanvas() {
  const ratio = window.devicePixelRatio || 1;
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  canvas.width = width * ratio;
  canvas.height = height * ratio;
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  invalidateRoomGeometry();
}

function invalidateRoomGeometry() {
  cachedRoomGeometry = { key: "", rooms: [] };
}

window.addEventListener("resize", resizeCanvas);
resizeCanvas();

class SpriteLibrary {
  constructor(spriteManifest) {
    this.manifest = spriteManifest;
    this.images = new Map();
    this.placeholderCache = new Map();
    const residentKeys = Object.keys(spriteManifest.residents || {});
    this.defaultPersona = residentKeys.length ? residentKeys[0] : null;
  }

  async loadAll() {
    const paths = new Set();
    const collect = (value) => {
      if (!value) return;
      if (Array.isArray(value)) {
        value.forEach((entry) => collect(entry));
      } else if (typeof value === "object") {
        Object.values(value).forEach((entry) => collect(entry));
      } else if (typeof value === "string") {
        paths.add(value);
      }
    };
    collect(this.manifest.building);
    collect(this.manifest.rooms);
    collect(this.manifest.residents);
    collect(this.manifest.props);

    await Promise.all(
      Array.from(paths).map((path) => this.loadImage(path))
    );
  }

  async loadImage(path) {
    if (this.images.has(path)) {
      return this.images.get(path);
    }
    return new Promise((resolve) => {
      const img = new Image();
      img.onload = () => {
        this.images.set(path, img);
        resolve(img);
      };
      img.onerror = () => {
        const placeholder = this.createPlaceholder(path);
        this.images.set(path, placeholder);
        resolve(placeholder);
      };
      img.src = path;
    });
  }

  createPlaceholder(key) {
    if (this.placeholderCache.has(key)) {
      return this.placeholderCache.get(key);
    }
    const seed = hashId(key);
    const hue = Math.floor(seed * 360);
    const canvasElem = document.createElement("canvas");
    canvasElem.width = 96;
    canvasElem.height = 96;
    const context = canvasElem.getContext("2d");
    context.fillStyle = `hsl(${hue}, 40%, 28%)`;
    context.fillRect(0, 0, canvasElem.width, canvasElem.height);
    context.fillStyle = "rgba(255,255,255,0.65)";
    context.font = "bold 12px 'Inter', sans-serif";
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.fillText(key.split("/").pop() || "sprite", canvasElem.width / 2, canvasElem.height / 2);
    this.placeholderCache.set(key, canvasElem);
    return canvasElem;
  }

  getImage(path) {
    if (!path) {
      return this.createPlaceholder("missing");
    }
    return this.images.get(path) || this.createPlaceholder(path);
  }

  getBuildingSprite(name) {
    const entry = this.manifest.building?.[name];
    if (!entry) return this.createPlaceholder(`building-${name}`);
    if (typeof entry === "string") return this.getImage(entry);
    const result = {};
    Object.entries(entry).forEach(([key, value]) => {
      result[key] = this.getImage(value);
    });
    return result;
  }

  getRoomDefinition(roomType) {
    const rooms = this.manifest.rooms || {};
    if (rooms[roomType]) return rooms[roomType];
    if (rooms.unit_1br) return rooms.unit_1br;
    const firstKey = Object.keys(rooms)[0];
    return rooms[firstKey] || null;
  }

  getRoomBackground(roomType) {
    const def = this.getRoomDefinition(roomType);
    if (!def) return this.createPlaceholder(`room-${roomType}`);
    const background =
      typeof def.background === "string" ? def.background : def.background?.path;
    return background ? this.getImage(background) : this.createPlaceholder(`room-${roomType}`);
  }

  getRoomProps(roomType) {
    const def = this.getRoomDefinition(roomType);
    if (!def || !def.props) return [];
    return def.props.map((entry) => {
      if (typeof entry === "string") {
        return {
          sprite: this.getImage(entry),
          layer: "mid",
          anchor: { x: 0.5, y: 0.9 },
          size: 0.4,
        };
      }
      const spritePath = entry.path || entry.sprite || entry.image;
      return {
        sprite: this.getImage(spritePath),
        layer: entry.layer || "mid",
        anchor: entry.anchor || { x: 0.5, y: 0.9 },
        size: entry.size ?? 0.4,
        flip: entry.flip || false,
      };
    });
  }

  getRoomActivityPoints(roomType) {
    const def = this.getRoomDefinition(roomType);
    return def?.activity_points || {};
  }

  getRoomCharacterScale(roomType) {
    const def = this.getRoomDefinition(roomType);
    return def?.character_scale ?? 0.7;
  }

  getLightingSprite(kind) {
    const overlay = this.manifest.props?.lighting_overlays?.[kind];
    return overlay ? this.getImage(overlay) : this.createPlaceholder(`lighting-${kind}`);
  }

  getPersonaDefinition(persona) {
    const residents = this.manifest.residents || {};
    if (residents[persona]) return residents[persona];
    if (this.defaultPersona) return residents[this.defaultPersona];
    const firstKey = Object.keys(residents)[0];
    return residents[firstKey] || {};
  }

  getPersonaFrames(persona, key) {
    const def = this.getPersonaDefinition(persona);
    const entry = def?.[key];
    if (!entry) return [];
    if (Array.isArray(entry)) return entry.map((path) => this.getImage(path));
    return [this.getImage(entry)];
  }
}

function hashId(id) {
  let hash = 0;
  for (let i = 0; i < id.length; i += 1) {
    hash = (hash * 31 + id.charCodeAt(i)) >>> 0;
  }
  return (hash % 1000) / 1000;
}

function seededRandom(seed) {
  let state = Math.floor(hashId(seed) * 1_000_000);
  return () => {
    state = (state * 1664525 + 1013904223) % 2 ** 32;
    return state / 2 ** 32;
  };
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function layerRank(layer) {
  return LAYER_ORDER[layer] ?? 1;
}

async function loadSprites() {
  const response = await fetch(MANIFEST_URL);
  if (!response.ok) {
    throw new Error(`Failed to load sprite manifest (${response.status})`);
  }
  manifest = await response.json();
  spriteLibrary = new SpriteLibrary(manifest);
  await spriteLibrary.loadAll();
  assetsReady = true;
}

async function pollState() {
  try {
    const response = await fetch(STATE_URL);
    const data = await response.json();
    if (!building) {
      building = [...data.building].sort((a, b) => a.floor - b.floor);
      rebuildRoomLookup();
    }
    if (currentState) {
      previousState = currentState;
      previousMap = new Map(previousState.residents.map((r) => [r.resident_id, r]));
    }
    currentState = data;
    lastUpdateTime = performance.now();
    if (data.speed) {
      currentSpeed = data.speed;
      reflectSpeedButtons();
    }
    updateHud(data);
  } catch (error) {
    console.error("Failed to fetch state", error);
  } finally {
    setTimeout(pollState, UPDATE_INTERVAL);
  }
}

function updateHud(state) {
  clockEl.textContent = state.clock;
  daylightEl.textContent = state.sunlight.is_day ? "Sunlit skyline" : "Moonlit lull";

  activityList.innerHTML = "";
  Object.entries(state.activity_breakdown)
    .sort((a, b) => b[1] - a[1])
    .forEach(([label, value]) => {
      const li = document.createElement("li");
      li.innerHTML = `<span>${label.replace("_", " ")}</span><span class="value">${value}</span>`;
      activityList.appendChild(li);
    });

  amenityList.innerHTML = "";
  const amenities = Object.entries(state.amenity_load)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);
  if (amenities.length === 0) {
    const li = document.createElement("li");
    li.textContent = "All calm across amenities.";
    amenityList.appendChild(li);
  } else {
    amenities.forEach(([label, value]) => {
      const li = document.createElement("li");
      li.innerHTML = `<span>${label}</span><span class="value">${value}</span>`;
      amenityList.appendChild(li);
    });
  }

  residentList.innerHTML = "";
  [...state.residents]
    .sort((a, b) => b.mood - a.mood)
    .slice(0, 6)
    .forEach((resident) => {
      const li = document.createElement("li");
      li.innerHTML = `
        <span class="name">${resident.name}</span>
        <span class="detail">${resident.persona.replace("_", " ")} • ${resident.activity}</span>
      `;
      residentList.appendChild(li);
    });

  eventList.innerHTML = "";
  state.events
    .slice(-7)
    .reverse()
    .forEach((event) => {
      const li = document.createElement("li");
      const time = new Date(event.timestamp).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      });
      li.innerHTML = `<span class="time">${time}</span>${event.resident} • ${event.description}`;
      eventList.appendChild(li);
    });
}

function reflectSpeedButtons() {
  speedButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.speed === currentSpeed);
  });
}

async function setSpeed(speed) {
  if (speed === currentSpeed) return;
  try {
    const response = await fetch(SPEED_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ speed }),
    });
    if (!response.ok) {
      throw new Error(`Speed change failed: ${response.status}`);
    }
    currentSpeed = speed;
    reflectSpeedButtons();
  } catch (error) {
    console.error(error);
  }
}

speedButtons.forEach((button) => {
  button.addEventListener("click", () => setSpeed(button.dataset.speed));
});

function lerp(a, b, t) {
  return a + (b - a) * t;
}

function towerMetrics(width, height) {
  const floorCount = building.length;
  const maxTowerHeight = Math.max(320, height - 160);
  const floorHeight = Math.min(30, maxTowerHeight / Math.max(1, floorCount + 2));
  const towerHeight = floorHeight * floorCount;
  const baseY = height - 90;
  const buildingWidth = Math.min(width * 0.58, 720);
  const offsetX = (width - buildingWidth) * 0.42;
  return { floorHeight, towerHeight, baseY, buildingWidth, offsetX };
}

function rebuildRoomLookup() {
  roomLookup = new Map();
  if (!building) return;
  building.forEach((floor) => {
    floor.units.forEach((unit) => {
      roomLookup.set(unit.unit, { room_type: unit.room_type, category: "unit" });
    });
    floor.amenities.forEach((amenity) => {
      roomLookup.set(amenity.name, {
        room_type: amenity.room_type || amenity.category,
        category: "amenity",
      });
    });
  });
}

function computeRoomGeometry(layout) {
  if (!building) return [];
  const layoutKey = `${layout.buildingWidth.toFixed(2)}:${layout.floorHeight.toFixed(2)}:${layout.offsetX.toFixed(2)}`;
  if (cachedRoomGeometry.key === layoutKey) {
    return cachedRoomGeometry.rooms;
  }

  const rooms = [];
  building.forEach((floor, index) => {
    const floorBaseY = layout.baseY - index * layout.floorHeight;
    const floorTop = floorBaseY - layout.floorHeight;
    const paddingY = layout.floorHeight * 0.12;
    const usableHeight = layout.floorHeight - paddingY * 2;

    floor.units.forEach((unit) => {
      const center = layout.offsetX + layout.buildingWidth * unit.position;
      const roomWidth = layout.buildingWidth * unit.width;
      const room = {
        label: unit.unit,
        type: unit.room_type,
        category: "unit",
        floor: floor.floor,
        x: center - roomWidth / 2,
        y: floorTop + paddingY,
        width: roomWidth,
        height: usableHeight,
      };
      rooms.push(room);
    });

    floor.amenities.forEach((amenity) => {
      const center = layout.offsetX + layout.buildingWidth * amenity.x;
      const amenityWidth = layout.buildingWidth * amenity.width;
      const room = {
        label: amenity.name,
        type: amenity.room_type || amenity.category,
        category: "amenity",
        floor: floor.floor,
        x: center - amenityWidth / 2,
        y: floorTop + paddingY,
        width: amenityWidth,
        height: usableHeight,
      };
      rooms.push(room);
    });
  });

  cachedRoomGeometry = { key: layoutKey, rooms };
  return rooms;
}

function groupResidentsByLocation(rooms) {
  const roomSet = new Set(rooms.map((room) => room.label));
  const roomResidents = new Map();
  const elevatorResidents = [];
  const waitingResidents = [];
  const outsideResidents = [];
  const hallwayResidents = [];

  currentState.residents.forEach((resident) => {
    if (roomSet.has(resident.location)) {
      const list = roomResidents.get(resident.location) || [];
      list.push(resident);
      roomResidents.set(resident.location, list);
      return;
    }
    if (resident.status === "in_elevator") {
      elevatorResidents.push(resident);
      return;
    }
    if (resident.status === "waiting_elevator") {
      waitingResidents.push(resident);
      return;
    }
    if (resident.location_type === "outside") {
      outsideResidents.push(resident);
      return;
    }
    hallwayResidents.push(resident);
  });

  return {
    roomResidents,
    elevatorResidents,
    waitingResidents,
    outsideResidents,
    hallwayResidents,
  };
}

function computeLightingTargets(roomResidents) {
  const lit = new Set();
  roomResidents.forEach((residents, label) => {
    if (
      residents.some(
        (resident) =>
          resident.status === "in_event" &&
          resident.activity !== "sleep" &&
          resident.activity !== "at_home"
      )
    ) {
      lit.add(label);
    }
  });
  return lit;
}

function drawSky(sunlight, width, height) {
  const gradient = ctx.createLinearGradient(0, 0, 0, height);
  if (sunlight.is_day) {
    gradient.addColorStop(0, `rgba(13, 94, 160, ${0.6 + sunlight.brightness * 0.4})`);
    gradient.addColorStop(1, `rgba(5, 12, 29, ${0.95 - sunlight.brightness * 0.3})`);
  } else {
    gradient.addColorStop(0, "rgba(4, 12, 32, 0.7)");
    gradient.addColorStop(1, "rgba(2, 5, 18, 1)");
  }
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, width, height);

  const angle = (currentState.minute_of_day / 1440) * Math.PI * 2;
  const orbitRadius = width * 0.35;
  const celestialX = width * 0.5 + Math.cos(angle) * orbitRadius * 0.4;
  const celestialY = height * 0.28 - Math.sin(angle) * orbitRadius * 0.18;
  const radius = sunlight.is_day ? 22 + sunlight.brightness * 18 : 16;

  ctx.beginPath();
  ctx.arc(celestialX, celestialY, radius, 0, Math.PI * 2);
  ctx.fillStyle = sunlight.is_day ? "rgba(255, 223, 125, 0.9)" : "rgba(214, 230, 255, 0.72)";
  ctx.shadowColor = sunlight.is_day ? "rgba(255, 215, 140, 0.55)" : "rgba(148, 197, 255, 0.35)";
  ctx.shadowBlur = sunlight.is_day ? 45 : 35;
  ctx.fill();
  ctx.shadowBlur = 0;
}

function drawTower(layout) {
  const { floorHeight, towerHeight, baseY, buildingWidth, offsetX } = layout;
  const towerTop = baseY - towerHeight;
  const facade = spriteLibrary.getBuildingSprite("facade");
  ctx.drawImage(facade, offsetX, towerTop, buildingWidth, towerHeight);

  const windowSprite = spriteLibrary.getBuildingSprite(
    currentState.sunlight.is_day ? "windows_day" : "windows_night"
  );
  if (windowSprite) {
    ctx.globalAlpha = currentState.sunlight.is_day ? 0.85 : 0.95;
    ctx.drawImage(windowSprite, offsetX, towerTop, buildingWidth, towerHeight);
    ctx.globalAlpha = 1;
  }

  ctx.fillStyle = "rgba(172, 204, 255, 0.48)";
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  ctx.font = `${Math.max(11, floorHeight * 0.4)}px 'Inter', sans-serif`;
  building.forEach((floor, index) => {
    const y = baseY - index * floorHeight;
    ctx.fillText(floor.label, offsetX - 12, y - floorHeight / 2);
  });
}

function drawRoomOutlines(rooms) {
  ctx.save();
  ctx.strokeStyle = "rgba(8, 12, 22, 0.38)";
  ctx.lineWidth = 1.5;
  rooms.forEach((room) => {
    ctx.strokeRect(room.x + 0.5, room.y + 0.5, room.width - 1, room.height - 1);
  });
  ctx.restore();
}

function drawRooms(layout, rooms, roomResidentsMap) {
  rooms.forEach((room) => {
    const background = spriteLibrary.getRoomBackground(room.type);
    ctx.drawImage(background, room.x, room.y, room.width, room.height);

    const props = spriteLibrary
      .getRoomProps(room.type)
      .slice()
      .sort((a, b) => layerRank(a.layer) - layerRank(b.layer));

    const backgroundProps = props.filter((prop) => prop.layer !== "foreground");
    const foregroundProps = props.filter((prop) => prop.layer === "foreground");

    backgroundProps.forEach((prop) => drawRoomProp(room, prop));

    const residents = roomResidentsMap.get(room.label) || [];
    renderResidentsInRoom(room, residents);

    foregroundProps.forEach((prop) => drawRoomProp(room, prop));
  });
}

function drawRoomProp(room, prop) {
  const anchor = prop.anchor || { x: 0.5, y: 0.9 };
  const baseWidth = room.width * (prop.size ?? 0.4);
  const aspect = prop.sprite.height > 0 ? prop.sprite.height / prop.sprite.width : 1;
  const width = baseWidth;
  const height = width * aspect;
  const x = room.x + room.width * anchor.x - width / 2;
  const y = room.y + room.height * anchor.y - height;

  ctx.save();
  if (prop.flip) {
    ctx.translate(x + width / 2, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(prop.sprite, -width / 2, y, width, height);
  } else {
    ctx.drawImage(prop.sprite, x, y, width, height);
  }
  ctx.restore();
}

function normalizeActivityPoints(points) {
  const normalized = {};
  if (!points) {
    return normalized;
  }
  Object.entries(points).forEach(([key, value]) => {
    normalized[key.toLowerCase()] = value;
  });
  return normalized;
}

function resolveActivityAnchor(points, resident, room, index, total) {
  const normalized = normalizeActivityPoints(points);
  const candidates = [];
  if (resident.activity) {
    candidates.push(resident.activity);
    candidates.push(`activity_${resident.activity}`);
  }
  if (resident.activity === "amenity" && room.type) {
    candidates.push(`amenity_${room.type}`);
  }
  if (room.type) {
    candidates.push(room.type);
  }
  if (room.category) {
    candidates.push(room.category);
  }
  candidates.push("default");

  let anchor = null;
  for (const key of candidates) {
    const match = normalized[key.toLowerCase()];
    if (match) {
      anchor = match;
      break;
    }
  }
  if (!anchor) {
    anchor = DEFAULT_ACTIVITY_ANCHOR;
  }

  const baseX = anchor.x ?? DEFAULT_ACTIVITY_ANCHOR.x;
  const baseY = anchor.y ?? DEFAULT_ACTIVITY_ANCHOR.y;
  if (total <= 1) {
    return { x: baseX, y: baseY };
  }
  const span = 0.12;
  const offset = (index - (total - 1) / 2) * span;
  return {
    x: clamp(baseX + offset, 0.2, 0.8),
    y: baseY,
  };
}

function renderResidentsInRoom(room, residents) {
  if (!residents.length) return;
  const activityPoints = spriteLibrary.getRoomActivityPoints(room.type);
  const characterScale = spriteLibrary.getRoomCharacterScale(room.type);

  residents.forEach((resident, index) => {
    const sprite = chooseResidentSprite(resident, roomLookup.get(resident.location));
    if (!sprite) return;
    const anchor = resolveActivityAnchor(activityPoints, resident, room, index, residents.length);
    const baseX = room.x + room.width * anchor.x;
    const baseY = room.y + room.height * anchor.y;
    const scale = (room.height * characterScale) / sprite.height;
    const width = sprite.width * scale;
    const height = sprite.height * scale;
    ctx.drawImage(sprite, baseX - width / 2, baseY - height, width, height);
  });
}

function drawElevatorResidents(layout, residents) {
  if (!residents.length) return;
  const { baseY, floorHeight, buildingWidth, offsetX } = layout;
  const spread = floorHeight * 0.12;
  residents.forEach((resident, index) => {
    const sprite = chooseResidentSprite(resident, roomLookup.get(resident.location));
    if (!sprite) return;
    const scale = (floorHeight * 0.7) / sprite.height;
    const width = sprite.width * scale;
    const height = sprite.height * scale;
    const baseXPixel =
      offsetX +
      buildingWidth * ELEVATOR_X +
      (index - (residents.length - 1) / 2) * spread;
    const baseYPixel =
      baseY - resident.vertical_position * floorHeight - floorHeight * 0.1;
    ctx.drawImage(sprite, baseXPixel - width / 2, baseYPixel - height, width, height);
  });
}

function drawWaitingResidents(layout, residents) {
  if (!residents.length) return;
  const { baseY, floorHeight, buildingWidth, offsetX } = layout;
  const spread = floorHeight * 0.14;
  residents.forEach((resident, index) => {
    const sprite = chooseResidentSprite(resident, roomLookup.get(resident.location));
    if (!sprite) return;
    const scale = (floorHeight * 0.65) / sprite.height;
    const width = sprite.width * scale;
    const height = sprite.height * scale;
    const baseXPixel =
      offsetX +
      buildingWidth * ELEVATOR_X +
      (index - (residents.length - 1) / 2) * spread;
    const floorValue = resident.vertical_position ?? resident.floor ?? 0;
    const baseYPixel = baseYCoordinate(baseY, floorValue, floorHeight) - floorHeight * 0.25;
    ctx.drawImage(sprite, baseXPixel - width / 2, baseYPixel - height, width, height);
  });
}

function drawOutsideResidents(layout, residents) {
  if (!residents.length) return;
  const { baseY, offsetX } = layout;
  const groundY = baseY + 40;
  residents.forEach((resident, index) => {
    const sprite = chooseResidentSprite(resident, roomLookup.get(resident.location));
    if (!sprite) return;
    const scale = 0.6;
    const width = sprite.width * scale;
    const height = sprite.height * scale;
    const jitter = (index - (residents.length - 1) / 2) * 60;
    const baseXPixel = offsetX - 90 + jitter;
    ctx.drawImage(sprite, baseXPixel - width / 2, groundY - height, width, height);
  });
}

function drawHallwayResidents(layout, residents, progress) {
  if (!residents.length) return;
  const { baseY, buildingWidth, offsetX, floorHeight } = layout;
  residents.forEach((resident) => {
    const sprite = chooseResidentSprite(resident, roomLookup.get(resident.location));
    if (!sprite) return;
    const scale = (floorHeight * 0.65) / sprite.height;
    const width = sprite.width * scale;
    const height = sprite.height * scale;
    const prev = previousMap.get(resident.resident_id) || resident;
    const interpX = previousState ? lerp(prev.x, resident.x, progress) : resident.x;
    const interpFloor = previousState
      ? lerp(prev.vertical_position, resident.vertical_position, progress)
      : resident.vertical_position;
    const baseXPixel = offsetX + buildingWidth * interpX;
    const baseYPixel = baseYCoordinate(baseY, interpFloor, floorHeight) - floorHeight * 0.2;
    ctx.drawImage(sprite, baseXPixel - width / 2, baseYPixel - height, width, height);
  });
}

function drawElevator(layout, elevator) {
  const { towerHeight, baseY, buildingWidth, offsetX, floorHeight } = layout;
  const shaft = spriteLibrary.getBuildingSprite("elevator_shaft");
  const carSprites = spriteLibrary.getBuildingSprite("elevator_car");
  const towerTop = baseY - towerHeight;
  const shaftWidth = Math.max(32, buildingWidth * 0.08);
  const shaftX = offsetX + buildingWidth * ELEVATOR_X - shaftWidth / 2;
  ctx.drawImage(shaft, shaftX, towerTop, shaftWidth, towerHeight);

  const carHeight = floorHeight * 0.8;
  const carY = baseY - elevator.position * floorHeight - carHeight * 0.5;
  const carSprite = elevator.doors_open ? carSprites.door_open : carSprites.idle;
  ctx.drawImage(carSprite, shaftX + 2, carY, shaftWidth - 4, carHeight);
}

function chooseResidentSprite(resident, roomMeta) {
  const personaFrames = spriteLibrary.getPersonaDefinition(resident.persona);
  const sequence = (key, frameMs = WALK_FRAME_MS) => {
    const frames = spriteLibrary.getPersonaFrames(resident.persona, key);
    if (!frames.length) return null;
    const idx = Math.floor(performance.now() / frameMs) % frames.length;
    return frames[idx];
  };

  const single = (key) => {
    const frames = spriteLibrary.getPersonaFrames(resident.persona, key);
    return frames.length ? frames[0] : null;
  };

  if (resident.status === "walking") {
    return sequence("walk");
  }
  if (resident.status === "waiting_elevator") {
    return sequence("idle", IDLE_FRAME_MS) || sequence("walk");
  }
  if (resident.status === "in_elevator") {
    return single("idle") || sequence("walk");
  }
  if (resident.status === "in_event") {
    if (resident.activity === "work" && personaFrames.work) {
      return single("work");
    }
    if (roomMeta?.room_type) {
      const amenityKey = `amenity_${roomMeta.room_type}`;
      if (personaFrames[amenityKey]) {
        return single(amenityKey);
      }
    }
    if (roomMeta?.category === "unit" && personaFrames.home) {
      return single("home");
    }
    if (resident.activity === "sleep" && personaFrames.sleep) {
      return single("sleep");
    }
    return sequence("idle", IDLE_FRAME_MS) || sequence("walk");
  }
  return sequence("idle", IDLE_FRAME_MS) || sequence("walk");
}

function baseYCoordinate(baseY, interpFloor, floorHeight) {
  return baseY - interpFloor * floorHeight - floorHeight * 0.2;
}

function drawLighting(layout, rooms, lightingTargets) {
  if (currentState.sunlight.is_day) return;
  const windows = spriteLibrary.getBuildingSprite("windows_night");
  const { floorHeight, towerHeight, baseY, buildingWidth, offsetX } = layout;
  const towerTop = baseY - towerHeight;
  ctx.globalAlpha = 0.15;
  ctx.drawImage(windows, offsetX, towerTop, buildingWidth, towerHeight);
  ctx.globalAlpha = 1;

  const roomMap = new Map(rooms.map((room) => [room.label, room]));
  lightingTargets.forEach((label) => {
    const roomRect = roomMap.get(label);
    if (!roomRect) return;
    const roomGlow = spriteLibrary.getLightingSprite("room_glow");
    ctx.globalAlpha = 0.35;
    ctx.drawImage(roomGlow, roomRect.x, roomRect.y, roomRect.width, roomRect.height);
    ctx.globalAlpha = 0.4;
    const windowGlow = spriteLibrary.getLightingSprite("window_glow");
    ctx.drawImage(windowGlow, roomRect.x, roomRect.y, roomRect.width, roomRect.height);
    ctx.globalAlpha = 1;
  });
}

function drawScene() {
  requestAnimationFrame(drawScene);
  if (!assetsReady || !currentState || !building) {
    return;
  }
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  const progress = previousState
    ? Math.min((performance.now() - lastUpdateTime) / UPDATE_INTERVAL, 1)
    : 1;

  const layout = towerMetrics(width, height);
  const rooms = computeRoomGeometry(layout);
  const groups = groupResidentsByLocation(rooms);
  const lightingTargets = computeLightingTargets(groups.roomResidents);

  ctx.clearRect(0, 0, width, height);
  drawSky(currentState.sunlight, width, height);
  drawTower(layout);
  drawRooms(layout, rooms, groups.roomResidents);
  drawRoomOutlines(rooms);
  drawElevator(layout, currentState.elevator);
  drawElevatorResidents(layout, groups.elevatorResidents);
  drawWaitingResidents(layout, groups.waitingResidents);
  drawHallwayResidents(layout, groups.hallwayResidents, progress);
  drawOutsideResidents(layout, groups.outsideResidents);
  drawLighting(layout, rooms, lightingTargets);
}

async function bootstrap() {
  try {
    await loadSprites();
    await pollState();
    drawScene();
  } catch (error) {
    console.error("Initialization failed", error);
  }
}

bootstrap();
