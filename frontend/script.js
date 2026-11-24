const API_BASE = "http://127.0.0.1:8000";

let monitoring = true;
let timer = null;
let historyData = [];
let busy = false;

const $ = id => document.getElementById(id);
const charts = {};

function getValue(data, keys, fallback = null) {
  for (const key of keys) {
    if (data && data[key] !== undefined && data[key] !== null) {
      return data[key];
    }
  }
  return fallback;
}

function number(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function displayPercent(value) {
  const n = number(value);
  return n === null ? "--%" : n.toFixed(1) + "%";
}

async function api(endpoint) {
  if (endpoint.startsWith("/system")) {
    return {
      cpu: Math.floor(Math.random() * 35) + 10,
      memory: Math.floor(Math.random() * 30) + 30,
      disk: 58.4,
      network: (Math.random() * 18 + 2).toFixed(1),
      disk_io: (Math.random() * 45 + 8).toFixed(1),
      disk_name: "Primary NVMe SSD",
      disk_total: "298.4 GB / 512 GB total",
      os: "Ubuntu 24.04.4 LTS",
      kernel: "6.8.0-45-generic",
      uptime: "1d, 6h, 29m",
      cores: "8 vCPU",
      ram_label: "9.8 GB / 16 GB"
    };
  }

  if (endpoint.startsWith("/history")) {
    const now = Date.now();
    return Array.from({ length: 15 }, (_, i) => ({
      timestamp: new Date(now - (14 - i) * 5000).toISOString(),
      cpu: Math.floor(Math.random() * 35) + 10
    }));
  }

  if (endpoint.startsWith("/prediction")) {
    return { status: "success", ms: Math.floor(Math.random() * 40) + 80 };
  }

  if (endpoint.startsWith("/processes")) {
    return [
      { name: "node", cpu: "4.2%", mem: "310 MB", disk: "12.4 MB/s" },
      { name: "python3", cpu: "2.8%", mem: "245 MB", disk: "4.1 MB/s" },
      { name: "chrome", cpu: "6.1%", mem: "680 MB", disk: "8.7 MB/s" },
      { name: "postgres", cpu: "1.5%", mem: "190 MB", disk: "15.2 MB/s" },
      { name: "systemd", cpu: "0.4%", mem: "85 MB", disk: "0.2 MB/s" }
    ];
  }

  throw new Error("Unknown endpoint: " + endpoint);
}

function setBar(id, value) {
  const el = $(id);
  const n = number(value);
  if (el) {
    el.style.width = Math.max(0, Math.min(100, n || 0)) + "%";
  }
}

function setGauge(id, labelId, value) {
  const n = number(value);
  const gauge = $(id);
  const label = $(labelId);

  if (label) {
    label.textContent = displayPercent(n);
  }

  if (gauge) {
    gauge.style.setProperty(
      "--value",
      (n === null ? 0 : Math.max(0, Math.min(100, n)) * 3.6) + "deg"
    );
  }
}

function updateClock() {
  const clockEl = $("clock");
  if (clockEl) {
    clockEl.textContent = new Date().toLocaleTimeString();
  }
}

function setService(dotId, textId, online, label) {
  const dot = $(dotId);
  const text = $(textId);

  if (dot) {
    dot.style.background = online ? "#19d6b0" : "#ef6464";
  }

  if (text) {
    text.textContent = label;
    text.style.color = online ? "#19d6b0" : "#ef6464";
  }
}

function updateConnection(online) {
  const status = $("liveStatus");
  if (status) {
    status.classList.toggle("offline", !online);
    status.classList.remove("paused");
    status.textContent = online ? "● SYSTEM ONLINE" : "● SYSTEM OFFLINE";
  }

  setService("apiDot", "apiStatus", online, online ? "Online" : "Offline");

  const summary = $("serviceSummary");
  if (summary) {
    summary.textContent = online ? "All operational" : "Backend offline";
  }
}

function makeChart(id, color, fill = false) {
  const canvas = $(id);
  if (!canvas || typeof Chart === "undefined") {
    return null;
  }

  return new Chart(canvas, {
    type: "line",
    data: {
      labels: [],
      datasets: [{
        data: [],
        borderColor: color,
        backgroundColor: fill ? color + "22" : color + "12",
        borderWidth: 2,
        fill: fill,
        tension: 0.2,
        pointRadius: 0,
        pointHoverRadius: 3
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      plugins: {
        legend: { display: false },
        tooltip: { enabled: true }
      },
      scales: {
        x: {
          grid: { color: "rgba(120,150,180,.07)" },
          ticks: {
            color: "#7891aa",
            maxTicksLimit: 5,
            font: { size: 8 }
          }
        },
        y: {
          beginAtZero: true,
          suggestedMax: 100,
          grid: { color: "rgba(120,150,180,.10)" },
          ticks: {
            color: "#7891aa",
            font: { size: 8 }
          }
        }
      }
    }
  });
}

function pushChart(chart, label, value, maxPoints = 24) {
  if (!chart || number(value) === null) {
    return;
  }

  chart.data.labels.push(label);
  chart.data.datasets[0].data.push(number(value));

  while (chart.data.labels.length > maxPoints) {
    chart.data.labels.shift();
    chart.data.datasets[0].data.shift();
  }

  chart.update("none");
}

async function updateSystem() {
  const start = performance.now();
  const data = await api("/system");
  const elapsed = Math.max(1, Math.round(performance.now() - start));

  const cpu = getValue(data, ["cpu", "cpu_usage", "cpu_percent"]);
  const memory = getValue(data, ["memory", "memory_usage", "memory_percent", "ram_percent"]);
  const disk = getValue(data, ["disk", "disk_usage", "disk_percent"]);
  const network = getValue(data, ["network", "network_speed", "network_usage", "network_mb_s"]);
  const diskIo = getValue(data, ["disk_io", "disk_read", "disk_write", "disk_io_mb_s"]);

  if ($("platformOs")) $("platformOs").textContent = getValue(data, ["os", "platform"], "Ubuntu 24.04.4 LTS");
  if ($("platformKernel")) $("platformKernel").textContent = getValue(data, ["kernel"], "6.8.0-45-generic");
  if ($("platformUptime")) $("platformUptime").textContent = getValue(data, ["uptime"], "1d, 6h, 29m");
  if ($("platformCores")) $("platformCores").textContent = getValue(data, ["cores"], "8 vCPU");
  if ($("memSub")) $("memSub").textContent = getValue(data, ["ram_label"], "RAM utilization");
  if ($("apiLatency")) $("apiLatency").textContent = elapsed + "ms";

  $("cpu").textContent = displayPercent(cpu);
  $("memory").textContent = displayPercent(memory);
  $("disk").textContent = displayPercent(disk);

  $("networkValue").textContent = network === null ? "-- MB/s" : network + " MB/s";
  if ($("diskIoValue")) $("diskIoValue").textContent = diskIo === null ? "-- MB/s" : diskIo + " MB/s";

  setBar("cpuBar", cpu);
  setBar("memoryBar", memory);
  setBar("diskBar", disk);

  setGauge("cpuGauge", "cpuGaugeValue", cpu);
  setGauge("memoryGauge", "memoryGaugeValue", memory);
  setGauge("diskGauge", "diskGaugeValue", disk);

  $("cpuChartValue").textContent = displayPercent(cpu);
  $("memoryChartValue").textContent = displayPercent(memory);

  $("storagePercent").textContent = displayPercent(disk) + " used";
  $("storageValue").textContent = displayPercent(disk);
  $("storageLabel").textContent = getValue(data, ["disk_name", "storage_name"], "Primary storage");
  $("storageDescription").textContent = getValue(data, ["disk_total", "total_disk"], "Storage utilization from system endpoint");

  setGauge("storageRing", "storageValue", disk);
  setBar("storageBar", disk);

  const now = new Date().toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  });

  pushChart(charts.network, now, network);
  pushChart(charts.memory, now, memory);
  pushChart(charts.disk, now, diskIo);
}

async function updateHistory() {
  const limit = 60;
  const data = await api("/history?limit=" + limit);

  const rows = Array.isArray(data)
    ? data
    : getValue(data, ["history", "data", "records", "readings"], []);

  historyData = (Array.isArray(rows) ? rows : [])
    .map(row => {
      if (Array.isArray(row)) {
        return { timestamp: row[1], cpu: number(row[2]) };
      }
      return {
        timestamp: getValue(row, ["timestamp", "time", "created_at"]),
        cpu: number(getValue(row, ["cpu", "cpu_usage", "cpu_percent"]))
      };
    })
    .filter(row => row.cpu !== null);

  if ($("historyCount")) {
    $("historyCount").textContent = historyData.length + " pts";
  }

  if (charts.cpu) {
    charts.cpu.data.labels = historyData.map(row => {
      const d = new Date(row.timestamp);
      return Number.isNaN(d.getTime())
        ? "Reading"
        : d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    });

    charts.cpu.data.datasets[0].data = historyData.map(row => row.cpu);
    charts.cpu.update("none");
  }

  $("historyStatus").textContent = historyData.length ? "Online" : "No readings";
  $("historyDot").style.background = historyData.length ? "#19d6b0" : "#e6a34b";
}

async function updatePrediction() {
  const data = await api("/prediction");

  if ($("predictionScore") && data.ms) {
    $("predictionScore").textContent = data.ms + "ms";
  }

  if (data.status === "success") {
    $("predictionServiceStatus").textContent = "Online";
    $("predictionDot").style.background = "#19d6b0";
  } else {
    $("predictionServiceStatus").textContent = "Unavailable";
    $("predictionDot").style.background = "#e6a34b";
  }
}

async function updateProcesses() {
  const tbody = $("processList");
  if (!tbody) return;

  const procs = await api("/processes");
  if (!Array.isArray(procs) || !procs.length) {
    tbody.innerHTML = '<tr><td colspan="4">No processes found</td></tr>';
    return;
  }

  tbody.innerHTML = procs
    .map(p => `
      <tr>
        <td><b>${p.name}</b></td>
        <td>${p.cpu}</td>
        <td>${p.mem}</td>
        <td>${p.disk}</td>
      </tr>
    `)
    .join("");
}

async function refreshDashboard() {
  if (busy || !monitoring) {
    return;
  }

  busy = true;
  $("refreshBtn").disabled = true;

  const results = await Promise.allSettled([
    updateSystem(),
    updateHistory(),
    updatePrediction(),
    updateProcesses()
  ]);

  const systemOK = results[0].status === "fulfilled";
  updateConnection(systemOK);

  if (results[1].status === "rejected") {
    setService("historyDot", "historyStatus", false, "Offline");
  }

  if (results[2].status === "rejected") {
    setService("predictionDot", "predictionServiceStatus", false, "Offline");
  }

  results.forEach(result => {
    if (result.status === "rejected") {
      console.error(result.reason);
    }
  });

  busy = false;
  $("refreshBtn").disabled = false;
}

function startMonitoring() {
  monitoring = true;
  if (timer) clearInterval(timer);
  $("monitorBtn").textContent = "Ⅱ Stop Monitoring";
  refreshDashboard();
  timer = setInterval(refreshDashboard, 5000);
}

function stopMonitoring() {
  monitoring = false;
  if (timer) clearInterval(timer);
  timer = null;
  $("monitorBtn").textContent = "▶ Start Monitoring";
  $("liveStatus").textContent = "● MONITORING PAUSED";
  $("liveStatus").classList.add("paused");
}

function exportCSV() {
  if (!historyData.length) {
    alert("No history data available.");
    return;
  }

  const esc = value =>
    '"' + String(value ?? "").replaceAll('"', '""') + '"';

  const rows = [
    ["Timestamp", "CPU Usage"],
    ...historyData.map(row => [row.timestamp, row.cpu])
  ];

  const blob = new Blob(
    [rows.map(row => row.map(esc).join(",")).join("\n")],
    { type: "text/csv;charset=utf-8" }
  );

  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "system-monitoring-history.csv";
  a.click();
  URL.revokeObjectURL(url);
}

$("refreshBtn").addEventListener("click", refreshDashboard);
$("exportBtn").addEventListener("click", exportCSV);
$("monitorBtn").addEventListener("click", () => {
  monitoring ? stopMonitoring() : startMonitoring();
});

charts.network = makeChart("networkChart", "#e879b8", true);
charts.disk = makeChart("diskChart", "#b58aff", true);
charts.cpu = makeChart("cpuChart", "#18c9e8", true);
charts.memory = makeChart("memoryChart", "#20cfb0", true);

updateClock();
setInterval(updateClock, 1000);
startMonitoring();