/* MikroTik 4D Syslog Analyzer — dashboard client */

const socket = io();
let timelineChart, serviceChart, dnsChart, pairsChart;

const svcColors = {
  dhcp: "#10b981",
  dns: "#06b6d4",
  firewall: "#f59e0b",
  hotspot: "#8b5cf6",
  system: "#6b7280",
  vpn: "#ec4899",
  wireless: "#14b8a6",
  routing: "#6366f1",
};

async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  return res.json();
}

function setBadge(online, text) {
  const el = document.getElementById("statusBadge");
  el.textContent = text || (online ? "Connected" : "Offline");
  el.className = "badge " + (online ? "online" : "offline");
}

async function refreshStats() {
  const stats = await api("/api/stats");
  document.getElementById("kpiTotal").textContent = stats.total || 0;
  document.getElementById("kpiDhcp").textContent = stats.by_service?.dhcp || 0;
  document.getElementById("kpiDns").textContent = stats.by_service?.dns || 0;
  document.getElementById("kpiFirewall").textContent = stats.by_service?.firewall || 0;
  updateCharts(stats);
}

async function refresh4D() {
  const data = await api("/api/analyzer/4d");
  renderFlow3D(data.flow_matrix);
  renderDhcpFlow(data.dhcp_timeline);
}

function renderFlow3D(matrix) {
  if (!matrix.length) {
    Plotly.newPlot("flow3d", [{ type: "scatter3d", mode: "markers", x: [0], y: [0], z: [0], marker: { size: 1 } }], {
      paper_bgcolor: "#111827", plot_bgcolor: "#111827", font: { color: "#e5e7eb" },
      title: { text: "Waiting for log data…", font: { color: "#9ca3af", size: 14 } },
    }, { responsive: true });
    return;
  }

  const services = [...new Set(matrix.map((m) => m.service))];
  const traces = services.map((svc) => {
    const pts = matrix.filter((m) => m.service === svc);
    return {
      type: "scatter3d",
      mode: "markers",
      name: svc.toUpperCase(),
      x: pts.map((p) => p.source),
      y: pts.map((p) => p.destination),
      z: pts.map((p) => p.time),
      text: pts.map((p) => `${p.source} → ${p.destination}<br>${p.service}: ${p.count}`),
      hoverinfo: "text",
      marker: {
        size: pts.map((p) => Math.min(20, 4 + Math.log2(p.count + 1) * 3)),
        color: svcColors[svc] || "#6b7280",
        opacity: 0.85,
      },
    };
  });

  Plotly.newPlot("flow3d", traces, {
    paper_bgcolor: "#111827",
    scene: {
      bgcolor: "#0a0e17",
      xaxis: { title: "Source IP", color: "#9ca3af", gridcolor: "#1f2937" },
      yaxis: { title: "Destination / DNS", color: "#9ca3af", gridcolor: "#1f2937" },
      zaxis: { title: "Time", color: "#9ca3af", gridcolor: "#1f2937" },
    },
    margin: { l: 0, r: 0, t: 30, b: 0 },
    legend: { font: { color: "#e5e7eb" } },
    font: { color: "#e5e7eb" },
  }, { responsive: true });
}

function renderDhcpFlow(rows) {
  const el = document.getElementById("dhcpFlow");
  if (!rows.length) {
    el.innerHTML = '<p style="color:#9ca3af">No DHCP events yet. Connect to your MikroTik and enable DHCP logging.</p>';
    return;
  }
  el.innerHTML = rows.slice(-30).reverse().map((r) => `
    <div class="flow-item">
      <span class="ts">${r.time}</span>
      <span class="action ${r.action}">${r.action || "event"}</span>
      <span>${r.client} ${r.mac ? "· " + r.mac : ""} ${r.hostname ? "· " + r.hostname : ""}</span>
    </div>
  `).join("");
}

function updateCharts(stats) {
  const tl = stats.timeline || [];
  if (timelineChart) timelineChart.destroy();
  timelineChart = new Chart(document.getElementById("timelineChart"), {
    type: "line",
    data: {
      labels: tl.map((t) => t.time),
      datasets: [{ label: "Events", data: tl.map((t) => t.count), borderColor: "#06b6d4", tension: 0.3, fill: true, backgroundColor: "rgba(6,182,212,0.1)" }],
    },
    options: chartOpts(),
  });

  const svc = stats.by_service || {};
  if (serviceChart) serviceChart.destroy();
  serviceChart = new Chart(document.getElementById("serviceChart"), {
    type: "doughnut",
    data: {
      labels: Object.keys(svc),
      datasets: [{ data: Object.values(svc), backgroundColor: Object.keys(svc).map((k) => svcColors[k] || "#6b7280") }],
    },
    options: { ...chartOpts(), plugins: { legend: { position: "right" } } },
  });

  const dns = stats.top_dns || [];
  if (dnsChart) dnsChart.destroy();
  dnsChart = new Chart(document.getElementById("dnsChart"), {
    type: "bar",
    data: {
      labels: dns.map((d) => d.query),
      datasets: [{ label: "Queries", data: dns.map((d) => d.count), backgroundColor: "#06b6d4" }],
    },
    options: { ...chartOpts(), indexAxis: "y" },
  });

  const pairs = stats.top_ip_pairs || [];
  if (pairsChart) pairsChart.destroy();
  pairsChart = new Chart(document.getElementById("pairsChart"), {
    type: "bar",
    data: {
      labels: pairs.map((p) => p.pair),
      datasets: [{ label: "Hits", data: pairs.map((p) => p.count), backgroundColor: "#8b5cf6" }],
    },
    options: { ...chartOpts(), indexAxis: "y" },
  });
}

function chartOpts() {
  return {
    responsive: true,
    plugins: { legend: { labels: { color: "#9ca3af" } } },
    scales: {
      x: { ticks: { color: "#9ca3af" }, grid: { color: "#1f2937" } },
      y: { ticks: { color: "#9ca3af" }, grid: { color: "#1f2937" } },
    },
  };
}

async function loadLogs() {
  const q = document.getElementById("logSearch").value;
  const svc = document.getElementById("logService").value;
  const params = new URLSearchParams({ limit: 100 });
  if (q) params.set("q", q);
  if (svc) params.set("service", svc);
  const logs = await api("/api/logs?" + params);
  const stream = document.getElementById("logStream");
  stream.innerHTML = logs.map((l) => `
    <div class="log-line">
      <span class="ts">${l.timestamp}</span>
      <span class="svc-${l.service}">[${l.service}]</span>
      ${l.message}
    </div>
  `).join("");
}

function appendLog(l) {
  const stream = document.getElementById("logStream");
  const svc = document.getElementById("logService").value;
  const q = document.getElementById("logSearch").value.toLowerCase();
  if (svc && l.service !== svc) return;
  if (q && !l.message.toLowerCase().includes(q) && !l.raw.toLowerCase().includes(q)) return;

  const div = document.createElement("div");
  div.className = "log-line";
  div.innerHTML = `<span class="ts">${l.timestamp}</span> <span class="svc-${l.service}">[${l.service}]</span> ${l.message}`;
  stream.prepend(div);
  while (stream.children.length > 200) stream.removeChild(stream.lastChild);
}

document.getElementById("connectBtn").addEventListener("click", async () => {
  const host = document.getElementById("routerIp").value.trim();
  const user = document.getElementById("routerUser").value.trim();
  const password = document.getElementById("routerPass").value;
  const setup_syslog = document.getElementById("setupSyslog").checked;

  setBadge(false, "Connecting…");
  try {
    const res = await api("/api/connect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ host, user, password, setup_syslog }),
    });
    if (res.ok) {
      setBadge(true, `Connected · ${res.imported_logs} logs imported`);
      document.getElementById("kpiRouter").textContent = host;
      await refreshStats();
      await refresh4D();
      await loadLogs();
    } else {
      setBadge(false, res.error || "Failed");
    }
  } catch (e) {
    setBadge(false, "Connection error");
  }
});

document.getElementById("logSearch").addEventListener("input", loadLogs);
document.getElementById("logService").addEventListener("change", loadLogs);

socket.on("new_log", (event) => {
  appendLog(event);
  refreshStats();
});

async function init() {
  const status = await api("/api/status");
  document.getElementById("kpiRouter").textContent = status.router_ip;
  setBadge(status.router_reachable, status.router_reachable ? "Router reachable" : "Awaiting connection");
  await refreshStats();
  await refresh4D();
  await loadLogs();
  setInterval(refreshStats, 15000);
  setInterval(refresh4D, 30000);
}

init();
