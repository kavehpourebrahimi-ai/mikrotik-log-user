/* MikroTik Log Analyzer — FortiAnalyzer-style client */

const socket = io();
let timelineChart, serviceChart, dnsChart;
const PAGE_TITLES = {
  dashboard: "داشبورد", users: "کاربران", ppp: "PPP / VPN",
  hotspot: "Hotspot", dns: "DNS", dhcp: "DHCP", login: "ورود به روتر", logs: "پشته لاگ",
};

function filterParams() {
  const p = new URLSearchParams();
  p.set("limit", "500");
  const df = document.getElementById("dateFrom").value;
  const dt = document.getElementById("dateTo").value;
  if (df) p.set("date_from", df.replace("T", " "));
  if (dt) p.set("date_to", dt.replace("T", " "));
  ["filterSourceIp", "filterDestIp", "filterUsername", "logSearch"].forEach(id => {
    const v = document.getElementById(id).value.trim();
    const key = id === "logSearch" ? "q" : id === "filterSourceIp" ? "source_ip" : id === "filterDestIp" ? "dest_ip" : "username";
    if (v) p.set(key, v);
  });
  p.set("sort_by", document.getElementById("sortBy").value);
  p.set("sort_order", document.getElementById("sortOrder").value);
  const svc = document.getElementById("logService")?.value;
  if (svc) p.set("service", svc);
  return p;
}

async function api(path, opts = {}) { return (await fetch(path, opts)).json(); }

function setBadge(on, text) {
  const el = document.getElementById("statusBadge");
  el.textContent = text || (on ? "متصل" : "قطع");
  el.className = "badge " + (on ? "on" : "off");
}

function fillTable(sel, rows, cols, fmt = {}) {
  const tb = document.querySelector(sel);
  if (!tb) return;
  tb.innerHTML = rows.length ? rows.map(r =>
    `<tr>${cols.map(c => {
      const v = fmt[c] ? fmt[c](r) : (Array.isArray(r[c]) ? r[c].join(", ") : (r[c] ?? "—"));
      return `<td>${v}</td>`;
    }).join("")}</tr>`
  ).join("") : `<tr><td colspan="${cols.length}">داده‌ای نیست — MikroTik را وصل کنید و syslog را فعال کنید</td></tr>`;
}

// Navigation
document.querySelectorAll(".nav-item").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    const page = btn.dataset.page;
    document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
    document.getElementById("page-" + page)?.classList.add("active");
    document.getElementById("pageTitle").textContent = PAGE_TITLES[page] || page;
    loadPage(page);
  });
});

async function loadPage(page) {
  if (page === "dashboard") await refreshDashboard();
  else if (page === "users") await refreshUsers();
  else if (page === "ppp") await refreshPpp();
  else if (page === "hotspot") await refreshHotspot();
  else if (page === "dns") await refreshDns();
  else if (page === "dhcp") await refreshDhcp();
  else if (page === "login") await refreshLogin();
  else if (page === "logs") await refreshLogs();
}

async function refreshDashboard() {
  const [stats, ppp] = await Promise.all([
    api("/api/stats?" + filterParams()),
    api("/api/ppp?" + filterParams()),
  ]);
  document.getElementById("kpiTotal").textContent = stats.total || 0;
  document.getElementById("kpiPppActive").textContent = ppp.active_count || 0;
  document.getElementById("kpiHotspot").textContent = stats.by_service?.hotspot || 0;
  document.getElementById("kpiDns").textContent = stats.by_service?.dns || 0;
  document.getElementById("kpiLogin").textContent = stats.by_service?.login || 0;
  document.getElementById("sidebarLogCount").textContent = (stats.total || 0).toLocaleString("fa-IR") + " لاگ";

  const users = await api("/api/users?limit=1");
  document.getElementById("kpiUsers").textContent = users.total_users || 0;

  updateCharts(stats);
  const data = await api("/api/analyzer/4d?" + filterParams());
  renderFlow3D(data.flow_matrix);
}

async function refreshUsers() {
  const data = await api("/api/users?" + filterParams());
  const tb = document.querySelector("#usersTable tbody");
  tb.innerHTML = (data.users || []).map(u => `<tr>
    <td><strong>${u.username}</strong></td>
    <td>${u.total_logs}</td>
    <td>${Object.entries(u.services||{}).map(([k,v])=>k+":"+v).join(" · ")}</td>
    <td>${u.ppp_active ? "✅ "+(u.ppp_service||"").toUpperCase() : "—"}</td>
    <td>${u.hotspot_active ? "✅" : "—"}</td>
    <td>${(u.source_ips||[]).slice(0,3).join(", ")}</td>
    <td>${u.ppp_uptime || "—"}</td>
    <td>${u.last_seen || "—"}</td>
    <td><button class="btn-link" onclick="showUserDetail('${u.username}')">لاگ‌ها</button></td>
  </tr>`).join("") || `<tr><td colspan="9">کاربری یافت نشد</td></tr>`;
}

async function showUserDetail(username) {
  const data = await api("/api/users/" + encodeURIComponent(username) + "?" + filterParams());
  document.getElementById("userDetailPanel").classList.remove("hidden");
  document.getElementById("detailUsername").textContent = username;
  fillTable("#userLogsTable tbody", data.logs || [],
    ["timestamp", "service", "source_ip", "dest_ip", "action", "message"]);
}

async function refreshPpp() {
  const data = await api("/api/ppp?" + filterParams());

  // Service cards: L2TP, SSTP, IPIP, PPTP, etc.
  const summary = data.service_summary || {};
  const labels = { l2tp: "L2TP", sstp: "SSTP", ipip: "IPIP", pptp: "PPTP", pppoe: "PPPoE", ovpn: "OVPN", ppp: "PPP" };
  document.getElementById("vpnServiceCards").innerHTML = Object.entries(labels).map(([k, lbl]) =>
    `<div class="vpn-card"><div class="count">${summary[k] || 0}</div><div class="label">${lbl}</div></div>`
  ).join("");

  fillTable("#pppActiveTable tbody", data.active_sessions || [],
    ["username", "service_label", "address", "caller_id", "uptime", "bytes_in", "bytes_out", "interface"]);

  fillTable("#pppLogTable tbody", data.recent_log_events || [],
    ["timestamp", "username", "vpn_type", "action", "source_ip", "dest_ip", "message"]);
}

async function refreshHotspot() {
  const data = await api("/api/hotspot?" + filterParams());
  fillTable("#hsLiveTable tbody", data.live_sessions || [],
    ["username", "address", "mac", "uptime", "bytes_in", "bytes_out"]);
  fillTable("#hsLogTable tbody", (data.events || []).slice().reverse(),
    ["time", "username", "action", "source_ip", "dest_ip", "mac"]);
}

async function refreshDns() {
  const data = await api("/api/dns?" + filterParams());
  const rows = data.map(r => ({ ...r, source_ips: (r.source_ips||[]).join(", "), dest_ips: (r.dest_ips||[]).join(", ") }));
  fillTable("#dnsTable tbody", rows, ["query", "count", "source_ips", "dest_ips"]);
  if (dnsChart) dnsChart.destroy();
  dnsChart = new Chart(document.getElementById("dnsChart"), {
    type: "bar",
    data: { labels: data.slice(0,12).map(d=>d.query), datasets: [{ label: "Query", data: data.slice(0,12).map(d=>d.count), backgroundColor: "#4da6ff" }] },
    options: { indexAxis: "y", plugins: { legend: { display: false } } },
  });
}

async function refreshDhcp() {
  const data = await api("/api/dhcp?" + filterParams());
  const el = document.getElementById("dhcpFlow");
  el.innerHTML = (data || []).slice(-40).reverse().map(r =>
    `<div class="flow-item"><span>${r.time}</span><span class="action ${r.action}">${r.action}</span><span>${r.source_ip||""} → ${r.dest_ip||""} ${r.mac||""}</span></div>`
  ).join("") || "<p class='muted'>لاگ DHCP نیست</p>";
}

async function refreshLogin() {
  const data = await api("/api/login-audit?" + filterParams());
  fillTable("#loginUsersTable tbody", (data.users||[]).map(u => ({
    username: u.username, login_count: u.login_count,
    source_ips: (u.source_ips||[]).map(s=>`${s.ip} (${s.count}×)`).join(", "),
    last_seen: u.last_seen,
  })), ["username", "login_count", "source_ips", "last_seen"]);
}

async function refreshLogs() {
  const logs = await api("/api/logs?" + filterParams());
  document.getElementById("logStackCount").textContent = logs.length + " رکورد";
  fillTable("#logsTable tbody", logs,
    ["timestamp", "service", "username", "source_ip", "dest_ip", "message"]);
}

function renderFlow3D(matrix) {
  const el = document.getElementById("flow3d");
  if (!el) return;
  if (!matrix?.length) {
    Plotly.newPlot(el, [], { paper_bgcolor: "#22262e", title: { text: "در انتظار لاگ…" } }, { responsive: true });
    return;
  }
  const svcs = [...new Set(matrix.map(m => m.service))];
  Plotly.newPlot(el, svcs.map(svc => {
    const pts = matrix.filter(m => m.service === svc);
    return { type: "scatter3d", mode: "markers", name: svc,
      x: pts.map(p=>p.source), y: pts.map(p=>p.destination), z: pts.map(p=>p.time),
      marker: { size: 5, color: svc === "vpn" ? "#a78bfa" : "#e8582a" } };
  }), { paper_bgcolor: "#22262e", scene: { bgcolor: "#1a1d23" }, font: { color: "#e8eaed" } }, { responsive: true });
}

function updateCharts(stats) {
  const tl = stats.timeline || [];
  if (timelineChart) timelineChart.destroy();
  timelineChart = new Chart(document.getElementById("timelineChart"), {
    type: "line",
    data: { labels: tl.map(t=>t.time), datasets: [{ data: tl.map(t=>t.count), borderColor: "#e8582a", fill: true, backgroundColor: "rgba(232,88,42,0.1)", tension: 0.3 }] },
    options: { plugins: { legend: { display: false } } },
  });
  const svc = stats.by_service || {};
  if (serviceChart) serviceChart.destroy();
  serviceChart = new Chart(document.getElementById("serviceChart"), {
    type: "doughnut",
    data: { labels: Object.keys(svc), datasets: [{ data: Object.values(svc), backgroundColor: ["#e8582a","#4da6ff","#a78bfa","#3dd68c","#fbbf24","#06b6d4"] }] },
  });
}

let serviceChart;

document.getElementById("connectBtn").addEventListener("click", async () => {
  setBadge(false, "…");
  const res = await api("/api/connect", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      host: document.getElementById("routerIp").value.trim(),
      user: document.getElementById("routerUser").value.trim(),
      password: document.getElementById("routerPass").value,
      setup_syslog: document.getElementById("setupSyslog").checked,
    }),
  });
  if (res.ok) {
    setBadge(true, "متصل");
    document.getElementById("sidebarRouter").textContent = res.host;
    await refreshAll();
  } else setBadge(false, res.error || "خطا");
});

document.getElementById("syncBtn").addEventListener("click", async () => {
  await api("/api/sync", { method: "POST" });
  await refreshAll();
});

document.getElementById("applyFilter").addEventListener("click", refreshAll);
document.getElementById("logService")?.addEventListener("change", refreshLogs);

async function refreshAll() {
  const active = document.querySelector(".nav-item.active")?.dataset.page || "dashboard";
  await refreshDashboard();
  await loadPage(active);
}

socket.on("new_log", () => {
  const n = parseInt(document.getElementById("kpiTotal").textContent) || 0;
  document.getElementById("kpiTotal").textContent = n + 1;
  document.getElementById("sidebarLogCount").textContent = (n + 1).toLocaleString("fa-IR") + " لاگ";
});

async function init() {
  const st = await api("/api/status");
  document.getElementById("sidebarRouter").textContent = st.router_ip;
  document.getElementById("sidebarLogCount").textContent = (st.log_count||0).toLocaleString("fa-IR") + " لاگ";
  setBadge(st.router_reachable, st.router_reachable ? "روتر OK" : "منتظر");
  await refreshAll();
  setInterval(refreshDashboard, 20000);
}

window.showUserDetail = showUserDetail;
init();
