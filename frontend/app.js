const STATE_URL = "/state";
const SPEED_URL = "/speed";
const UPDATE_INTERVAL = 1200;
const ELEVATOR_X = 0.5;

const canvas = document.getElementById("twinCanvas");
const ctx = canvas.getContext("2d");
const clockEl = document.getElementById("clock");
const daylightEl = document.getElementById("daylight");
const activityList = document.getElementById("activityStats");
const amenityList = document.getElementById("amenityStats");
const residentList = document.getElementById("residentSpotlight");
const eventList = document.getElementById("eventFeed");
const speedButtons = Array.from(document.querySelectorAll(".speed"));

let building = null;
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
}

window.addEventListener("resize", resizeCanvas);
resizeCanvas();

async function pollState() {
  try {
    const response = await fetch(STATE_URL);
    const data = await response.json();
    if (!building) {
      building = [...data.building].sort((a, b) => a.floor - b.floor);
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
  const daylightLabel = state.sunlight.is_day ? "Sunlit skyline" : "Moonlit lull";
  daylightEl.textContent = daylightLabel;

  activityList.innerHTML = "";
  const activities = Object.entries(state.activity_breakdown).sort((a, b) => b[1] - a[1]);
  activities.forEach(([label, value]) => {
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
  const spotlight = [...state.residents]
    .sort((a, b) => b.mood - a.mood)
    .slice(0, 6);
  spotlight.forEach((resident) => {
    const li = document.createElement("li");
    li.innerHTML = `
      <span class="name">${resident.name}</span>
      <span class="detail">${resident.persona.replace("_", " ")} • ${resident.activity}</span>
    `;
    residentList.appendChild(li);
  });

  eventList.innerHTML = "";
  const events = state.events.slice(-7).reverse();
  events.forEach((event) => {
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
  if (speed === currentSpeed) {
    return;
  }
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

function hashId(id) {
  let hash = 0;
  for (let i = 0; i < id.length; i += 1) {
    hash = (hash * 31 + id.charCodeAt(i)) >>> 0;
  }
  return (hash % 1000) / 1000;
}

function towerMetrics(width, height) {
  const floorCount = building.length;
  const maxTowerHeight = Math.max(300, height - 160);
  const floorHeight = Math.min(26, maxTowerHeight / Math.max(1, floorCount + 3));
  const towerHeight = floorHeight * floorCount;
  const baseY = height - 90;
  const buildingWidth = Math.min(width * 0.55, 680);
  const offsetX = (width - buildingWidth) * 0.42;
  return { floorHeight, towerHeight, baseY, buildingWidth, offsetX };
}

function paintSky(sunlight, width, height) {
  const gradient = ctx.createLinearGradient(0, 0, 0, height);
  if (sunlight.is_day) {
    gradient.addColorStop(0, `rgba(13, 94, 160, ${0.6 + sunlight.brightness * 0.4})`);
    gradient.addColorStop(1, `rgba(5, 12, 29, ${0.95 - sunlight.brightness * 0.3})`);
  } else {
    gradient.addColorStop(0, `rgba(4, 12, 32, ${0.7})`);
    gradient.addColorStop(1, `rgba(2, 5, 18, ${1})`);
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

function drawTowerSkeleton(layout, width, height) {
  const { floorHeight, towerHeight, baseY, buildingWidth, offsetX } = layout;
  ctx.save();
  ctx.translate(offsetX, 0);

  const towerTop = baseY - towerHeight;
  const bodyGradient = ctx.createLinearGradient(0, towerTop, buildingWidth, baseY);
  bodyGradient.addColorStop(0, "rgba(25, 41, 82, 0.95)");
  bodyGradient.addColorStop(1, "rgba(12, 24, 55, 0.85)");
  ctx.fillStyle = bodyGradient;
  ctx.fillRect(0, towerTop, buildingWidth, towerHeight);

  ctx.strokeStyle = "rgba(84, 144, 255, 0.1)";
  ctx.lineWidth = 1;
  ctx.strokeRect(0, towerTop, buildingWidth, towerHeight);

  ctx.font = `${Math.max(10, floorHeight * 0.38)}px 'Inter', sans-serif`;
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";

  building.forEach((floor, index) => {
    const y = baseY - index * floorHeight;
    const fill = floor.floor === 52
      ? "rgba(255, 220, 140, 0.18)"
      : floor.amenities.length > 0
      ? "rgba(68, 115, 192, 0.12)"
      : "rgba(255, 255, 255, 0.03)";
    ctx.fillStyle = fill;
    ctx.fillRect(0, y - floorHeight, buildingWidth, floorHeight);
    ctx.strokeStyle = "rgba(120, 175, 255, 0.15)";
    ctx.beginPath();
    ctx.moveTo(0, y - floorHeight);
    ctx.lineTo(buildingWidth, y - floorHeight);
    ctx.stroke();

    ctx.fillStyle = "rgba(172, 204, 255, 0.48)";
    ctx.fillText(floor.label, -10, y - floorHeight / 2);
  });

  ctx.strokeStyle = "rgba(74, 120, 190, 0.12)";
  const verticalDivisions = 5;
  for (let i = 1; i < verticalDivisions; i += 1) {
    const x = (buildingWidth / verticalDivisions) * i;
    ctx.beginPath();
    ctx.moveTo(x, towerTop);
    ctx.lineTo(x, baseY);
    ctx.stroke();
  }

  ctx.restore();
}

function drawAmenities(layout) {
  const { floorHeight, baseY, buildingWidth, offsetX } = layout;
  ctx.save();
  ctx.translate(offsetX, 0);
  building.forEach((floor, index) => {
    if (!floor.amenities.length) {
      return;
    }
    floor.amenities.forEach((amenity) => {
      const y = baseY - index * floorHeight - floorHeight * 0.5;
      const x = buildingWidth * amenity.x;
      ctx.beginPath();
      ctx.arc(x, y, Math.max(4, floorHeight * 0.18), 0, Math.PI * 2);
      ctx.fillStyle = amenity.category === "lounge" ? "rgba(251, 191, 36, 0.85)" : "rgba(56, 189, 248, 0.75)";
      ctx.shadowColor = ctx.fillStyle;
      ctx.shadowBlur = 12;
      ctx.fill();
      ctx.shadowBlur = 0;
    });
  });
  ctx.restore();
}

function drawElevator(layout, elevator) {
  const { floorHeight, baseY, buildingWidth, offsetX, towerHeight } = layout;
  const towerTop = baseY - towerHeight;
  const shaftWidth = Math.max(26, buildingWidth * 0.08);
  const shaftX = offsetX + buildingWidth * ELEVATOR_X - shaftWidth / 2;
  const shaftHeight = towerHeight;

  ctx.save();
  const shaftGradient = ctx.createLinearGradient(shaftX, towerTop, shaftX + shaftWidth, baseY);
  shaftGradient.addColorStop(0, "rgba(11, 18, 38, 0.9)");
  shaftGradient.addColorStop(1, "rgba(6, 12, 26, 0.95)");
  ctx.fillStyle = shaftGradient;
  ctx.fillRect(shaftX, towerTop, shaftWidth, shaftHeight);
  ctx.strokeStyle = "rgba(94, 141, 220, 0.3)";
  ctx.strokeRect(shaftX, towerTop, shaftWidth, shaftHeight);

  const carHeight = floorHeight * 0.75;
  const carY = baseY - elevator.position * floorHeight - carHeight * 0.5;
  const doorGlow = elevator.doors_open ? "rgba(125, 211, 252, 0.8)" : "rgba(96, 165, 250, 0.55)";
  ctx.fillStyle = doorGlow;
  ctx.shadowColor = doorGlow;
  ctx.shadowBlur = elevator.doors_open ? 20 : 8;
  ctx.fillRect(shaftX + 3, carY, shaftWidth - 6, carHeight);
  ctx.shadowBlur = 0;
  ctx.restore();
}

function drawResidents(layout, progress) {
  if (!currentState) return;
  const { floorHeight, baseY, buildingWidth, offsetX } = layout;
  const now = performance.now();
  currentState.residents.forEach((resident) => {
    const prev = previousMap.get(resident.resident_id) || resident;
    let interpX = previousState ? lerp(prev.x, resident.x, progress) : resident.x;
    const interpY = previousState
      ? lerp(prev.vertical_position, resident.vertical_position, progress)
      : resident.vertical_position;
    let px;
    if (resident.status === "in_elevator") {
      px = offsetX + buildingWidth * ELEVATOR_X;
      interpX = ELEVATOR_X;
    } else {
      const pxBase = offsetX + buildingWidth * interpX;
      px = pxBase;
    }
    if (resident.location_type === "outside") {
      const jitter = hashId(resident.resident_id) * 40;
      px = offsetX - 60 + jitter;
    }
    const floorY = baseY - interpY * floorHeight;
    const bodyHeight = Math.max(floorHeight * 0.7, 14);
    const bodyWidth = Math.max(floorHeight * 0.45, 8);
    const headRadius = bodyWidth * 0.45;
    const sway = Math.sin(now / 600 + hashId(resident.resident_id) * Math.PI * 2) * 0.8;
    const base = floorY - 4;
    const bodyTop = base - bodyHeight;

    ctx.save();
    if (resident.status === "in_elevator") {
      ctx.shadowColor = "rgba(125, 211, 252, 0.6)";
      ctx.shadowBlur = 18;
    } else if (resident.location_type === "amenity") {
      ctx.shadowColor = "rgba(250, 204, 21, 0.45)";
      ctx.shadowBlur = 14;
    } else if (resident.status === "waiting_elevator") {
      ctx.shadowColor = "rgba(148, 163, 255, 0.35)";
      ctx.shadowBlur = 12;
    }

    ctx.fillStyle = resident.outfit_color;
    ctx.fillRect(px - bodyWidth / 2 + sway, bodyTop + headRadius, bodyWidth, bodyHeight - headRadius);

    ctx.fillStyle = resident.accent_color;
    ctx.fillRect(px - bodyWidth / 3 + sway, bodyTop + headRadius + (bodyHeight * 0.3), bodyWidth / 1.5, bodyHeight * 0.15);

    ctx.beginPath();
    ctx.arc(px + sway, bodyTop + headRadius, headRadius, 0, Math.PI * 2);
    ctx.fillStyle = resident.hair_color;
    ctx.fill();

    ctx.shadowBlur = 0;

    if (resident.status === "waiting_elevator") {
      ctx.strokeStyle = "rgba(148, 163, 255, 0.45)";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.arc(px + sway, bodyTop + headRadius, headRadius + 4, 0, Math.PI * 2);
      ctx.stroke();
    }

    if (resident.status === "walking") {
      ctx.fillStyle = "rgba(125, 211, 252, 0.25)";
      ctx.fillRect(px - bodyWidth / 2, base - 4, bodyWidth, 4);
    }

    ctx.restore();
  });
}

function drawScene() {
  requestAnimationFrame(drawScene);
  if (!currentState || !building) {
    return;
  }
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  const progress = previousState
    ? Math.min((performance.now() - lastUpdateTime) / UPDATE_INTERVAL, 1)
    : 1;

  const layout = towerMetrics(width, height);
  paintSky(currentState.sunlight, width, height);
  drawTowerSkeleton(layout, width, height);
  drawAmenities(layout);
  drawElevator(layout, currentState.elevator);
  drawResidents(layout, progress);
}

pollState();
drawScene();
