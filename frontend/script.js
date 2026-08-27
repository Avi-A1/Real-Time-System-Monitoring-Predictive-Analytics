const API_URL = "http://127.0.0.1:8000";

let cpuChart;
let memoryChart;

const maxDataPoints = 20;


// Format bytes into readable units
function formatBytes(bytes) {

    if (bytes < 1024) {
        return bytes + " B";
    }

    if (bytes < 1024 * 1024) {
        return (bytes / 1024).toFixed(2) + " KB";
    }

    if (bytes < 1024 * 1024 * 1024) {
        return (bytes / (1024 * 1024)).toFixed(2) + " MB";
    }

    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + " GB";
}


// Update the metric cards
function updateMetrics(data) {

    document.getElementById("cpu-value").textContent =
        data.cpu.toFixed(1) + "%";

    document.getElementById("memory-value").textContent =
        data.memory.toFixed(1) + "%";

    document.getElementById("disk-value").textContent =
        data.disk.toFixed(1) + "%";

    document.getElementById("process-value").textContent =
        data.running_processes;

    document.getElementById("network-sent").textContent =
        formatBytes(data.network_sent);

    document.getElementById("network-received").textContent =
        formatBytes(data.network_received);
}


// Update connection status
function updateStatus(connected) {

    const dot = document.getElementById("status-dot");
    const text = document.getElementById("status-text");

    if (connected) {
        dot.style.background = "#22c55e";
        text.textContent = "Connected";
    } else {
        dot.style.background = "#ef4444";
        text.textContent = "Disconnected";
    }
}


// Create charts
function createCharts() {

    const cpuContext =
        document.getElementById("cpu-chart").getContext("2d");

    const memoryContext =
        document.getElementById("memory-chart").getContext("2d");


    cpuChart = new Chart(cpuContext, {

        type: "line",

        data: {
            labels: [],
            datasets: [{
                label: "CPU %",
                data: [],
                tension: 0.3
            }]
        },

        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100
                }
            }
        }
    });


    memoryChart = new Chart(memoryContext, {

        type: "line",

        data: {
            labels: [],
            datasets: [{
                label: "Memory %",
                data: [],
                tension: 0.3
            }]
        },

        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100
                }
            }
        }
    });
}


// Add data to charts
function updateCharts(data) {

    const time = new Date().toLocaleTimeString();

    cpuChart.data.labels.push(time);
    cpuChart.data.datasets[0].data.push(data.cpu);

    memoryChart.data.labels.push(time);
    memoryChart.data.datasets[0].data.push(data.memory);


    if (cpuChart.data.labels.length > maxDataPoints) {

        cpuChart.data.labels.shift();
        cpuChart.data.datasets[0].data.shift();

        memoryChart.data.labels.shift();
        memoryChart.data.datasets[0].data.shift();
    }


    cpuChart.update();
    memoryChart.update();
}


// Get current system information
async function fetchSystemData() {

    try {

        const response =
            await fetch(`${API_URL}/system`);

        if (!response.ok) {
            throw new Error("API request failed");
        }

        const data = await response.json();

        updateMetrics(data);
        updateCharts(data);
        updateStatus(true);

    } catch (error) {

        console.error("Connection error:", error);

        updateStatus(false);
    }
}


// Start application
createCharts();

fetchSystemData();

// Update dashboard every 5 seconds
setInterval(fetchSystemData, 5000);