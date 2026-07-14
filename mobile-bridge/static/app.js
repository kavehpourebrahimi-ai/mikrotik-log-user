"use strict";

const el = (id) => document.getElementById(id);
const api = (path) => fetch(path).then((r) => {
  if (!r.ok) throw new Error(r.status + " " + r.statusText);
  return r.json();
});

let currentCam = null;
let hls = null;

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

function playHls(url) {
  const v = el("player");
  destroyPlayer();
  showMsg("در حال بارگذاری… (۱۰–۲۰ ثانیه صبر کنید)");
  const onReady = () => showMsg("");
  if (v.canPlayType("application/vnd.apple.mpegurl")) {
    v.src = url;
    v.addEventListener("loadeddata", onReady, { once: true });
    v.addEventListener("error", () => showMsg("خطا در پخش. دکمه ⟳ را بزنید."), { once: true });
    v.play().catch(() => {});
  } else if (window.Hls && Hls.isSupported()) {
    hls = new Hls({ lowLatencyMode: true, liveSyncDurationCount: 3, manifestLoadingTimeOut: 30000 });
    hls.loadSource(url);
    hls.attachMedia(v);
    hls.on(Hls.Events.MANIFEST_PARSED, () => { onReady(); v.play().catch(() => {}); });
    hls.on(Hls.Events.ERROR, (_e, d) => {
      if (d.fatal) showMsg("خطا در پخش زنده (" + (d.type || "hls") + "). دکمه ⟳ را بزنید.");
    });
  } else {
    showMsg("پخش‌کننده HLS لود نشد. صفحه را رفرش کنید.");
  }
}

function playMp4(url) {
  const v = el("player");
  destroyPlayer();
  showMsg("در حال آماده‌سازی ویدیو…");
  v.src = url;
  v.addEventListener("loadeddata", () => showMsg(""), { once: true });
  v.addEventListener("error", () => showMsg("پخش این بخش ممکن نشد."), { once: true });
  v.play().catch(() => {});
}

// ---- views -----------------------------------------------------------------
function showGrid() {
  currentCam = null;
  destroyPlayer();
  el("camView").classList.add("hidden");
  el("gridView").classList.remove("hidden");
  el("backBtn").classList.add("hidden");
  el("title").textContent = "دوربین‌ها";
}

function openCamera(cam) {
  currentCam = cam;
  el("gridView").classList.add("hidden");
  el("camView").classList.remove("hidden");
  el("backBtn").classList.remove("hidden");
  el("title").textContent = cam.name;
  selectTab("live");
}

// ---- camera grid -----------------------------------------------------------
async function loadCameras() {
  const grid = el("cameraGrid");
  grid.innerHTML = "";
  el("gridEmpty").classList.add("hidden");
  let cams = [];
  try {
    cams = await api("/api/cameras?refresh=1");
  } catch (e) {
    el("gridEmpty").textContent = "خطا در خواندن لیست دوربین‌ها: " + e.message;
    el("gridEmpty").classList.remove("hidden");
    return;
  }
  if (!cams.length) {
    el("gridEmpty").textContent = "دوربینی پیدا نشد. اتصال دیتابیس را بررسی کنید.";
    el("gridEmpty").classList.remove("hidden");
    return;
  }
  for (const cam of cams) {
    const card = document.createElement("div");
    card.className = "cam-card" + (cam.disabled ? " disabled" : "");
    card.innerHTML = `<div class="icon">📷</div><div class="name"></div>`;
    card.querySelector(".name").textContent = cam.name;
    card.addEventListener("click", () => openCamera(cam));
    grid.appendChild(card);
  }
}

// ---- tabs ------------------------------------------------------------------
function selectTab(name) {
  document.querySelectorAll(".tab").forEach((t) =>
    t.classList.toggle("active", t.dataset.tab === name));
  el("livePane").classList.toggle("hidden", name !== "live");
  el("playbackPane").classList.toggle("hidden", name !== "playback");
  if (name === "live") startLive();
  else { destroyPlayer(); loadDays(); }
}

// ---- live ------------------------------------------------------------------
async function waitForLive(url, guid, attempts = 45) {
  for (let i = 0; i < attempts; i++) {
    showMsg(`در حال اتصال… ${i + 1}/${attempts}`);
    try {
      const r = await fetch(url);
      if (r.ok) return true;
      if (r.status === 503) {
        await new Promise((res) => setTimeout(res, 3000));
        continue;
      }
      const err = await r.text();
      showMsg("خطا: " + err.slice(0, 400));
      return false;
    } catch (e) {
      showMsg("خطا در شبکه: " + e.message);
      return false;
    }
  }
  try {
    const st = await api(`/api/live/${guid}/status`);
    const hint = st.log_tail ? st.log_tail.slice(-200) : "ffmpeg log empty";
    showMsg("استریم آماده نشد. " + hint);
  } catch (_e) {
    showMsg("استریم آماده نشد. config.ini و ffmpeg.log را بررسی کنید.");
  }
  return false;
}

async function startLive() {
  if (!currentCam) return;
  el("livePane").innerHTML =
    '<p class="livehint">پخش زنده از طریق سرور… (ممکن است ۱–۲ دقیقه طول بکشد)</p>' +
    `<img id="liveSnap" alt="" style="max-width:100%;border-radius:10px;margin-top:8px;display:none" />`;
  const url = `/live/${currentCam.guid}/index.m3u8`;
  const snap = el("liveSnap");
  if (snap) {
    snap.style.display = "block";
    snap.src = `/api/live/${currentCam.guid}/snapshot.jpg?ts=${Date.now()}`;
    snap.onerror = () => { snap.style.display = "none"; };
  }
  const ok = await waitForLive(url, currentCam.guid);
  if (!ok) return;
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
  days.reverse(); // newest first
  for (const d of days) {
    const opt = document.createElement("option");
    opt.value = d; opt.textContent = d;
    sel.appendChild(opt);
  }
  loadSegments();
}

function fmtTime(iso) {
  const d = new Date(iso);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

async function loadSegments() {
  const date = el("daySelect").value;
  const list = el("segmentList");
  list.innerHTML = "";
  el("segEmpty").classList.add("hidden");
  if (!date) return;
  let segs = [];
  try {
    segs = await api(`/api/cameras/${currentCam.guid}/segments?date=${date}`);
  } catch (e) {}
  if (!segs.length) { el("segEmpty").classList.remove("hidden"); return; }
  for (const s of segs) {
    const item = document.createElement("div");
    item.className = "seg-item";
    const mins = Math.round(s.duration / 60);
    item.innerHTML = `<span class="time"></span><span class="dur"></span>`;
    item.querySelector(".time").textContent =
      `${fmtTime(s.begin_iso)} — ${fmtTime(s.end_iso)}`;
    item.querySelector(".dur").textContent = `${mins} دقیقه`;
    item.addEventListener("click", () => {
      playMp4(`/playback/${currentCam.guid}/segment?date=${date}&t=${s.begin}`);
    });
    list.appendChild(item);
  }
}

// ---- wire up ---------------------------------------------------------------
el("backBtn").addEventListener("click", showGrid);
el("refreshBtn").addEventListener("click", () => {
  if (currentCam) { if (el("livePane").classList.contains("hidden")) loadDays(); else startLive(); }
  else loadCameras();
});
document.querySelectorAll(".tab").forEach((t) =>
  t.addEventListener("click", () => selectTab(t.dataset.tab)));
el("daySelect").addEventListener("change", loadSegments);

loadCameras();
