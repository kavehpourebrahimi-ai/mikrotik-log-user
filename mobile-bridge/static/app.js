"use strict";

const el = (id) => document.getElementById(id);
const api = (path) => fetch(path).then((r) => {
  if (!r.ok) throw new Error(r.status + " " + r.statusText);
  return r.json();
});

let cameras = [];
let currentCam = null;
let hls = null;
let liveStream = "main";
let gridMode = "list";
let gridStream = "sub";
let multiTimer = null;
let appConfig = { grid_stream: "sub" };

// ---- video helpers ---------------------------------------------------------
function destroyPlayer() {
  const v = el("player");
  if (hls) { hls.destroy(); hls = null; }
  v.removeAttribute("src");
  v.load();
}

function showMsg(text) {
  const m = el("playerMsg");
  if (!text) { m.classList.add("hidden"); return; }
  m.textContent = text;
  m.classList.remove("hidden");
}

function plainError(text) {
  return text.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
}

function playHls(url) {
  const v = el("player");
  destroyPlayer();
  showMsg("در حال بارگذاری…");
  const onReady = () => showMsg("");
  if (v.canPlayType("application/vnd.apple.mpegurl")) {
    v.src = url;
    v.addEventListener("loadeddata", onReady, { once: true });
    v.addEventListener("error", () => showMsg("خطا در پخش."), { once: true });
    v.play().catch(() => {});
  } else if (window.Hls && Hls.isSupported()) {
    hls = new Hls({ lowLatencyMode: true, liveSyncDurationCount: 3, manifestLoadingTimeOut: 30000 });
    hls.loadSource(url);
    hls.attachMedia(v);
    hls.on(Hls.Events.MANIFEST_PARSED, () => { onReady(); v.play().catch(() => {}); });
    hls.on(Hls.Events.ERROR, (_e, d) => {
      if (d.fatal) showMsg("خطا در پخش زنده (" + (d.type || "hls") + ")");
    });
  } else {
    showMsg("پخش‌کننده HLS لود نشد.");
  }
}

function playMp4(url) {
  const v = el("player");
  destroyPlayer();
  showMsg("در حال آماده‌سازی…");
  v.src = url;
  v.addEventListener("loadeddata", () => showMsg(""), { once: true });
  v.addEventListener("error", () => showMsg("پخش ممکن نشد."), { once: true });
  v.play().catch(() => {});
}

function liveUrl(guid, stream) {
  return stream === "main"
    ? `/live/${guid}/index.m3u8`
    : `/live/${guid}/${stream}/index.m3u8`;
}

// ---- views -----------------------------------------------------------------
function stopMultiRefresh() {
  if (multiTimer) { clearInterval(multiTimer); multiTimer = null; }
}

function setGridMode(mode) {
  gridMode = mode;
  el("listViewBtn").classList.toggle("active", mode === "list");
  el("multiViewBtn").classList.toggle("active", mode === "multi");
  el("cameraGrid").parentElement.classList.toggle("hidden", mode !== "list");
  el("multiView").classList.toggle("hidden", mode !== "multi");
  if (mode === "multi") startMultiGrid();
  else stopMultiRefresh();
}

function showGrid() {
  currentCam = null;
  destroyPlayer();
  el("camView").classList.add("hidden");
  el("gridView").classList.remove("hidden");
  el("multiView").classList.toggle("hidden", gridMode !== "multi");
  el("viewToggle").classList.remove("hidden");
  el("backBtn").classList.add("hidden");
  el("title").textContent = "دوربین‌ها";
  if (gridMode === "multi") startMultiGrid();
}

function openCamera(cam) {
  currentCam = cam;
  stopMultiRefresh();
  el("gridView").classList.add("hidden");
  el("multiView").classList.add("hidden");
  el("viewToggle").classList.add("hidden");
  el("camView").classList.remove("hidden");
  el("backBtn").classList.remove("hidden");
  el("title").textContent = cam.name;
  selectTab("live");
}

// ---- camera list -----------------------------------------------------------
async function loadCameras() {
  el("gridEmpty").classList.add("hidden");
  try {
    cameras = await api("/api/cameras?refresh=1");
  } catch (e) {
    el("gridEmpty").textContent = "خطا: " + e.message;
    el("gridEmpty").classList.remove("hidden");
    return;
  }
  if (!cameras.length) {
    el("gridEmpty").textContent = "دوربینی پیدا نشد.";
    el("gridEmpty").classList.remove("hidden");
    return;
  }
  renderListGrid();
  if (gridMode === "multi") renderMultiGrid();
}

function renderListGrid() {
  const grid = el("cameraGrid");
  grid.innerHTML = "";
  for (const cam of cameras) {
    const card = document.createElement("div");
    card.className = "cam-card";
    card.innerHTML = `<div class="icon">📷</div><div class="name"></div>`;
    card.querySelector(".name").textContent = cam.name;
    card.addEventListener("click", () => openCamera(cam));
    grid.appendChild(card);
  }
}

function renderMultiGrid() {
  const grid = el("multiGrid");
  grid.innerHTML = "";
  for (const cam of cameras) {
    const card = document.createElement("div");
    card.className = "multi-card";
    const img = document.createElement("img");
    img.alt = cam.name;
    img.dataset.guid = cam.guid;
    img.src = `/api/live/${cam.guid}/snapshot.jpg?stream=${gridStream}&ts=${Date.now()}`;
    img.onerror = () => { img.style.opacity = "0.3"; };
    const name = document.createElement("div");
    name.className = "name";
    name.textContent = cam.name;
    card.appendChild(img);
    card.appendChild(name);
    card.addEventListener("click", () => openCamera(cam));
    grid.appendChild(card);
  }
}

function refreshMultiSnapshots() {
  document.querySelectorAll("#multiGrid img").forEach((img) => {
    img.src = `/api/live/${img.dataset.guid}/snapshot.jpg?stream=${gridStream}&ts=${Date.now()}`;
  });
}

function startMultiGrid() {
  if (!cameras.length) return;
  renderMultiGrid();
  stopMultiRefresh();
  multiTimer = setInterval(refreshMultiSnapshots, 4000);
}

// ---- tabs / live -----------------------------------------------------------
function selectTab(name) {
  document.querySelectorAll(".tab").forEach((t) =>
    t.classList.toggle("active", t.dataset.tab === name));
  el("livePane").classList.toggle("hidden", name !== "live");
  el("playbackPane").classList.toggle("hidden", name !== "playback");
  if (name === "live") startLive();
  else { destroyPlayer(); loadDays(); }
}

function setLiveStream(stream) {
  liveStream = stream;
  el("btnMain").classList.toggle("active", stream === "main");
  el("btnSub").classList.toggle("active", stream === "sub");
  if (currentCam && !el("livePane").classList.contains("hidden")) startLive();
}

async function waitForLive(url, guid, attempts = 20) {
  let lastDetail = "";
  for (let i = 0; i < attempts; i++) {
    showMsg(`در حال اتصال لایو… ${i + 1}/${attempts}`);
    try {
      const r = await fetch(url + (url.includes("?") ? "&" : "?") + "_=" + Date.now());
      if (r.ok) return true;
      const body = plainError(await r.text());
      lastDetail = body;
      if (r.status === 503) {
        // First ensure() already tried several URLs; short poll for segments.
        if (body.includes("--- ffmpeg ---") || body.includes("Diagnose:")) {
          // Hard failure — don't spin for minutes.
          if (!body.includes("stream starting, retry")) {
            showMsg("لایو وصل نشد:\n" + body.slice(0, 900));
            return false;
          }
        }
        await new Promise((res) => setTimeout(res, 2000));
        continue;
      }
      showMsg("خطا: " + body.slice(0, 500));
      return false;
    } catch (e) {
      showMsg("خطا: " + e.message);
      return false;
    }
  }
  showMsg("استریم آماده نشد.\n" + (lastDetail || "").slice(0, 700));
  return false;
}

async function showLiveDiagnose(guid, stream) {
  try {
    const d = await api(`/api/live/${guid}/diagnose?stream=${stream}`);
    const lines = (d.candidates || [])
      .slice(0, 8)
      .map((c) => `${c.probe_ok ? "OK" : "NO"} ${c.source}: ${c.url}`)
      .join("\n");
    showMsg(
      (d.ok ? "RTSP پیدا شد ولی ffmpeg HLS نساخت.\n" : "هیچ RTSP معتبری پیدا نشد.\n") +
      (d.onvif_error ? "ONVIF: " + d.onvif_error + "\n" : "") +
      lines +
      `\n\n/api/live/${guid}/diagnose?stream=${stream}`
    );
  } catch (e) {
    showMsg("diagnose failed: " + e.message);
  }
}

async function startLive() {
  if (!currentCam) return;
  const url = liveUrl(currentCam.guid, liveStream);
  const ok = await waitForLive(url, currentCam.guid);
  if (!ok) {
    await showLiveDiagnose(currentCam.guid, liveStream);
    return;
  }
  playHls(url);
}

// ---- playback --------------------------------------------------------------
async function loadDays() {
  const sel = el("daySelect");
  sel.innerHTML = "";
  let days = [];
  try { days = await api(`/api/cameras/${currentCam.guid}/days`); } catch (e) {}
  if (!days.length) {
    el("segmentList").innerHTML = "";
    el("segEmpty").classList.remove("hidden");
    return;
  }
  days.reverse();
  for (const d of days) {
    const opt = document.createElement("option");
    opt.value = d; opt.textContent = d;
    sel.appendChild(opt);
  }
  const now = new Date();
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60000);
  el("timePick").value = local.toISOString().slice(0, 16);
  loadSegments();
}

function fmtTime(iso) {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

async function loadSegments() {
  const date = el("daySelect").value;
  const list = el("segmentList");
  list.innerHTML = "";
  el("segEmpty").classList.add("hidden");
  if (!date) return;
  let segs = [];
  try { segs = await api(`/api/cameras/${currentCam.guid}/segments?date=${date}`); } catch (e) {}
  if (!segs.length) { el("segEmpty").classList.remove("hidden"); return; }
  for (const s of segs) {
    const item = document.createElement("div");
    item.className = "seg-item";
    item.innerHTML = `<span class="time"></span><span class="dur"></span>`;
    item.querySelector(".time").textContent =
      `${fmtTime(s.begin_iso)} — ${fmtTime(s.end_iso)}`;
    item.querySelector(".dur").textContent = `${Math.round(s.duration / 60)} دقیقه`;
    item.addEventListener("click", () => {
      playMp4(`/playback/${currentCam.guid}/segment?date=${date}&t=${s.begin}`);
    });
    list.appendChild(item);
  }
}

async function playAtTime() {
  if (!currentCam) return;
  const when = el("timePick").value;
  if (!when) return;
  showMsg("در حال پیدا کردن ضبط…");
  try {
    const info = await api(`/api/cameras/${currentCam.guid}/play_at?datetime=${encodeURIComponent(when)}`);
    el("daySelect").value = info.date;
    if (info.nearest) showMsg("نزدیک‌ترین بازه پیدا شد — در حال پخش…");
    playMp4(info.url);
  } catch (e) {
    showMsg("ضبطی برای این زمان نیست — از لیست بازه‌ها انتخاب کنید.");
  }
}

// ---- wire up ---------------------------------------------------------------
el("backBtn").addEventListener("click", showGrid);
el("refreshBtn").addEventListener("click", () => {
  if (currentCam) {
    if (el("playbackPane").classList.contains("hidden")) startLive();
    else loadDays();
  } else {
    loadCameras();
  }
});
document.querySelectorAll(".tab").forEach((t) =>
  t.addEventListener("click", () => selectTab(t.dataset.tab)));
el("daySelect").addEventListener("change", loadSegments);
el("playAtBtn").addEventListener("click", playAtTime);
el("btnMain").addEventListener("click", () => setLiveStream("main"));
el("btnSub").addEventListener("click", () => setLiveStream("sub"));
el("listViewBtn").addEventListener("click", () => setGridMode("list"));
el("multiViewBtn").addEventListener("click", () => setGridMode("multi"));

(async () => {
  try {
    appConfig = await api("/api/config");
    gridStream = appConfig.grid_stream || "sub";
  } catch (_e) { /* ignore */ }
  await loadCameras();
})();
