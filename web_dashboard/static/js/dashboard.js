/* MikroTik 4D Syslog Analyzer — dashboard client (فارسی) */

const socket = io();
let timelineChart, serviceChart, dnsChart;

const svcColors = {
  dhcp: "#10b981", dns: "#06b6d4", firewall: "#f59e0b", hotspot: "#8b5cf6",
  system: "#6b7280", vpn: "#ec4899", login: "#f97316", wireless: "#14b8a6", routing: "#6366f1",
};

function filterParams() {
  const p = new URLSearchParams();
  p.set("limit", "500");
  const df = document.getElementById("dateFrom").value;
  const dt = document.getElementById("dateTo").value;
  if (df) p.set("date_from", df.replace("T", " "));
  if (dt) p.set("date_to", dt.replace("T", " "));
  const src = document.getElementById("filterSourceIp").value.trim();
  const dst = document.getElementById("filterDestIp").value.trim();
  const user = document.getElementById("filterUsername").value.trim();
  const q = document.getElementById("logSearch").value.trim();
  if (src) p.set("source_ip", src);
  if (dst) p.set("dest_ip", dst);
  if (user) p.set("username", user);
  if (q) p.set("q", q);
  p.set("sort_by", document.getElementById("sortBy").value);
  p.set("sort_order", document.getElementById("sortOrder").value);
  const svc = document.getElementById("logService")?.value;
  if (svc) p.set("service", svc);
  return p;
}

async function api(path, opts = {}) {
  return (await fetch(path, opts)).json();
}

function setBadge(online, text) {
  const el = document.getElementById("statusBadge");
  el.textContent = text || (online ? "متصل" : "قطع");
  el.className = "badge " + (online ? "online" : "offline");
}

function fillTable(tbody, rows, cols) {
  tbody.innerHTML = rows.map(r =>
    `<tr>${cols.map(c => `<td>${r[c] ?? "—"}</td>`).join("")}</tr>`
  ).join("") || `<tr><td colspan="${cols.length}">داده‌ای موجود نیست</td></tr>`;
}

async function refreshStats() {
  const stats = await api("/api/stats?" + filterParams());
  document.getElementById("kpiTotal").textContent = stats.total || 0;
  document.getElementById("kpiVpn").textContent = stats.by_service?.vpn || 0;
  document.getElementById("kpiHotspot").textContent = stats.by_service?.hotspot || 0;
  document.getElementById("kpiDns").textContent = stats.by_service?.dns || 0;
  document.getElementById("kpiLogin").textContent = stats.by_service?.login || 0;
  updateCharts(stats);
}

async function refresh4D() {
  const data = await api("/api/analyzer/4d?" + filterParams());
  renderFlow3D(data.flow_matrix);
  renderDhcpFlow(data.dhcp_timeline);
}

async function refreshVpn() {
  const data = await api("/api/vpn?" + filterParams());
  document.getElementById("vpnSummary").innerHTML = `
    <span>کل رویداد VPN: <b>${data.total}</b></span>
    <span>انواع: ${Object.entries(data.by_type || {}).map(([k,v]) => k + ": " + v).join(" · ") || "—"}</span>
  `;
  fillTable(
    document.querySelector("#vpnTable tbody"),
    (data.sessions || []).slice().reverse(),
    ["time", "username", "vpn_type", "action", "source_ip", "dest_ip"]
  );
}

async function refreshHotspot() {
  const data = await api("/api/hotspot?" + filterParams());
  document.getElementById("hotspotSummary").innerHTML = `
    <span>کل رویداد: <b>${data.total}</b></span>
    <span>کاربران فعال: <b>${(data.users || []).length}</b></span>
  `;
  fillTable(
    document.querySelector("#hotspotTable tbody"),
    (data.events || []).slice().reverse(),
    ["time", "username", "action", "source_ip", "dest_ip", "mac"]
  );
}

async function refreshDns() {
  const data = await api("/api/dns?" + filterParams());
  const rows = data.map(r => ({
    ...r,
    source_ips: (r.source_ips || []).join(", "),
    dest_ips: (r.dest_ips || []).join(", "),
  }));
  fillTable(document.querySelector("#dnsTable tbody"), rows,
    ["query", "count", "source_ips", "dest_ips"]);

  if (dnsChart) dnsChart.destroy();
  dnsChart = new Chart(document.getElementById("dnsChart"), {
    type: "bar",
    data: {
      labels: data.slice(0, 15).map(d => d.query),
      datasets: [{ label: "تعداد", data: data.slice(0, 15).map(d => d.count), backgroundColor: "#06b6d4" }],
    },
    options: chartOpts(true),
  });
}

async function refreshLogin() {
  const data = await api("/api/login-audit?" + filterParams());
  document.getElementById("loginSummary").innerHTML = `
    <span>کل ورودها: <b>${data.total_logins}</b></span>
    <span>کاربران: <b>${(data.users || []).length}</b></span>
  `;
  const users = (data.users || []).map(u => ({
    username: u.username,
    login_count: u.login_count,
    last_seen: u.last_seen,
    source_ips: (u.source_ips || []).map(s => `${s.ip} (${s.count}×)`).join(", "),
  }));
  fillTable(document.querySelector("#loginUsersTable tbody"), users,
    ["username", "login_count", "last_seen", "source_ips"]);
  fillTable(document.querySelector("#loginEventsTable tbody"),
    (data.events || []).slice().reverse(),
    ["time", "username", "action", "source_ip"]);
}

async function loadLogs() {
  const logs = await api("/api/logs?" + filterParams());
  fillTable(
    document.getElementById("logStream"),
    logs,
    ["timestamp", "service", "source_ip", "dest_ip", "username", "message"]
  );
}

function renderFlow3D(matrix) {
  if (!matrix.length) {
    Plotly.newPlot("flow3d", [], {
      paper_bgcolor: "#111827", font: { color: "#e5e7eb" },
      title: { text: "در انتظار دریافت لاگ از MikroTik…", font: { color: "#9ca3af" } },
    }, { responsive: true });
    return;
  }
  const services = [...new Set(matrix.map(m => m.service))];
  const traces = services.map(svc => {
    const pts = matrix.filter(m => m.service === svc);
    return {
      type: "scatter3d", mode: "markers", name: svc.toUpperCase(),
      x: pts.map(p => p.source), y: pts.map(p => p.destination), z: pts.map(p => p.time),
      text: pts.map(p => `مبدأ: ${p.source}<br>مقصد: ${p.destination}<br>${p.service}: ${p.count}`),
      hoverinfo: "text",
      marker: { size: pts.map(p => Math.min(20, 4 + Math.log2(p.count + 1) * 3)), color: svcColors[svc] || "#6b7280", opacity: 0.85 },
    };
  });
  Plotly.newPlot("flow3d", traces, {
    paper_bgcolor: "#111827",
    scene: {
      bgcolor: "#0a0e17",
      xaxis: { title: "IP مبدأ", color: "#9ca3af" },
      yaxis: { title: "IP مقصد / DNS", color: "#9ca3af" },
      zaxis: { title: "زمان", color: "#9ca3af" },
    },
    font: { color: "#e5e7eb" },
  }, { responsive: true });
}

function renderDhcpFlow(rows) {
  const el = document.getElementById("dhcpFlow");
  if (!rows.length) { el.innerHTML = "<p class='muted'>رویداد DHCP یافت نشد.</p>"; return; }
  el.innerHTML = rows.slice(-40).reverse().map(r => `
    <div class="flow-item">
      <span class="ts">${r.time}</span>
      <span class="action ${r.action}">${r.action}</span>
      <span>مبدأ: ${r.source_ip || "—"} · مقصد: ${r.dest_ip || "—"} · ${r.mac || ""} ${r.hostname || ""}</span>
    </div>`).join("");
}

function updateCharts(stats) {
  const tl = stats.timeline || [];
  if (timelineChart) timelineChart.destroy();
  timelineChart = new Chart(document.getElementById("timelineChart"), {
    type: "line",
    data: { labels: tl.map(t => t.time), datasets: [{ label: "رویداد", data: tl.map(t => t.count), borderColor: "#06b6d4", tension: 0.3, fill: true, backgroundColor: "rgba(6,182,212,0.1)" }] },
    options: chartOpts(),
  });
  const svc = stats.by_service || {};
  if (serviceChart) serviceChart.destroy();
  serviceChart = new Chart(document.getElementById("serviceChart"), {
    type: "doughnut",
    data: { labels: Object.keys(svc), datasets: [{ data: Object.values(svc), backgroundColor: Object.keys(svc).map(k => svcColors[k] || "#6b7280") }] },
    options: { ...chartOpts(), plugins: { legend: { position: "right" } } },
  });
}

function chartOpts(horizontal) {
  const o = { responsive: true, plugins: { legend: { labels: { color: "#9ca3af" } } }, scales: { x: { ticks: { color: "#9ca3af" } }, y: { ticks: { color: "#9ca3af" } } } };
  if (horizontal) o.indexAxis = "y";
  return o;
}

let serviceChart;

async function refreshAll() {
  await refreshStats();
  await refresh4D();
  await refreshVpn();
  await refreshHotspot();
  await refreshDns();
  await refreshLogin();
  await loadLogs();
}

// Tabs
document.querySelectorAll(".tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    tab.classList.add("active");
    const name = tab.dataset.tab;
    document.querySelectorAll(".tab-panel").forEach(p => {
      const show = name === "overview"
        ? p.dataset.panel === "overview"
        : p.dataset.panel === name;
      p.classList.toggle("hidden", !show);
    });
  });
});

document.getElementById("connectBtn").addEventListener("click", async () => {
  const host = document.getElementById("routerIp").value.trim();
  const user = document.getElementById("routerUser").value.trim();
  const password = document.getElementById("routerPass").value;
  setBadge(false, "در حال اتصال…");
  try {
    const res = await api("/api/connect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ host, user, password, setup_syslog: document.getElementById("setupSyslog").checked }),
    });
    if (res.ok) {
      setBadge(true, `متصل · ${res.imported_logs} لاگ import شد`);
      document.getElementById("kpiRouter").textContent = host;
      await refreshAll();
    } else {
      setBadge(false, res.error || "خطا");
    }
  } catch { setBadge(false, "خطای اتصال"); }
});

document.getElementById("applyFilter").addEventListener("click", refreshAll);
document.getElementById("logService")?.addEventListener("change", loadLogs);
document.getElementById("sortBy").addEventListener("change", refreshAll);
document.getElementById("sortOrder").addEventListener("change", refreshAll);

socket.on("new_log", () => { refreshStats(); loadLogs(); });

async function init() {
  const status = await api("/api/status");
  document.getElementById("kpiRouter").textContent = status.router_ip;
  setBadge(status.router_reachable, status.router_reachable ? "روتر در دسترس" : "منتظر اتصال");
  await refreshAll();
  setInterval(refreshStats, 15000);
}

init();
