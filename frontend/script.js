const API_BASE = "http://127.0.0.1:8000";

/* =========================
   ELEMENTS
========================= */

const cpu = document.getElementById("cpu");
const memory = document.getElementById("memory");
const disk = document.getElementById("disk");
const network = document.getElementById("network");

const cpuBar = document.getElementById("cpuBar");
const memoryBar = document.getElementById("memoryBar");
const diskBar = document.getElementById("diskBar");

const time = document.getElementById("time");

const operatingSystem =
    document.getElementById("operatingSystem");

const processor =
    document.getElementById("processor");

const ram =
    document.getElementById("ram");

const predictionValue =
    document.getElementById("predictionValue");

const predictionDescription =
    document.getElementById("predictionDescription");

const predictionStatus =
    document.getElementById("predictionStatus");

const anomalyTitle =
    document.getElementById("anomalyTitle");

const anomalyDescription =
    document.getElementById("anomalyDescription");

const anomalyStatus =
    document.getElementById("anomalyStatus");

const chartRange =
    document.getElementById("chartRange");


/* =========================
   CPU CHART
========================= */

const ctx =
    document.getElementById("cpuChart");

const cpuChart = new Chart(ctx, {

    type: "line",

    data: {
        labels: [],
        datasets: [{
            label: "CPU Usage",
            data: [],
            borderColor: "#4f46e5",
            backgroundColor: "rgba(79,70,229,0.08)",
            borderWidth: 3,
            fill: true,
            tension: 0.4,
            pointRadius: 3
        }]
    },

    options: {

        responsive: true,

        maintainAspectRatio: false,

        animation: false,

        plugins: {
            legend: {
                display: false
            }
        },

        scales: {

            y: {
                min: 0,
                max: 100,

                ticks: {
                    callback: value =>
                        value + "%"
                }
            }
        }
    }
});


/* =========================
   TIME
========================= */

function updateTime() {

    const now = new Date();

    time.textContent =
        now.toLocaleTimeString();
}


/* =========================
   SYSTEM INFORMATION
========================= */

async function updateSystem() {

    try {

        const response =
            await fetch(
                `${API_BASE}/system`
            );

        const data =
            await response.json();


        /* CPU */

        cpu.textContent =
            `${Number(data.cpu).toFixed(1)}%`;

        cpuBar.style.width =
            `${data.cpu}%`;


        /* MEMORY */

        memory.textContent =
            `${Number(data.memory).toFixed(1)}%`;

        memoryBar.style.width =
            `${data.memory}%`;


        /* DISK */

        disk.textContent =
            `${Number(data.disk).toFixed(1)}%`;

        diskBar.style.width =
            `${data.disk}%`;


        /* NETWORK */

        const download = Number(data.network_download_speed);

        if (Number.isFinite(download)) {
            network.textContent = `${download.toFixed(2)} MB/s`;
        } else {
            network.textContent = "0.00 MB/s";
        }

        /* SYSTEM INFORMATION */

        operatingSystem.textContent =
            data.operating_system || "Unknown";

        processor.textContent =
            data.processor || "Unknown";

        ram.textContent =
            data.ram || "Unknown";


        updateTime();

    } catch (error) {

        console.error(
            "System error:",
            error
        );
    }
}


/* =========================
   CPU HISTORY / CHART
========================= */

async function updateChart() {

    try {

        let limit = 30;

        if (
            chartRange &&
            chartRange.value
        ) {

            limit =
                parseInt(
                    chartRange.value
                ) || 30;
        }


        const response =
            await fetch(
                `${API_BASE}/history?limit=${limit}`
            );

        const result =
            await response.json();


        const history =
            Array.isArray(result)
                ? result
                : result.history ||
                  result.data ||
                  [];


        const labels = [];
        const values = [];


        history.forEach(row => {

            /*
             * SQLite row:
             * [id, timestamp, cpu, ...]
             */

            if (Array.isArray(row)) {

                labels.push(
                    new Date(
                        row[1]
                    ).toLocaleTimeString()
                );

                values.push(
                    Number(row[2])
                );

            } else {

                labels.push(
                    new Date(
                        row.timestamp
                    ).toLocaleTimeString()
                );

                values.push(
                    Number(row.cpu)
                );
            }
        });


        if (values.length === 0) {
            return;
        }


        cpuChart.data.labels =
            labels;

        cpuChart.data.datasets[0].data =
            values;


        /*
         * Update without animation.
         */

        cpuChart.update("none");

    } catch (error) {

        console.error(
            "Chart error:",
            error
        );
    }
}


/* =========================
   AI PREDICTION
========================= */

async function updatePrediction() {

    try {

        const response =
            await fetch(
                `${API_BASE}/prediction`
            );

        const data =
            await response.json();


        if (
            data.status !==
            "success"
        ) {
            return;
        }


        const predicted =
            Number(
                data.predicted_future_cpu
            );

        const current =
            Number(
                data.current_cpu
            );


        predictionValue.textContent =
            `${predicted.toFixed(1)}%`;


        if (
            predicted >
            current + 2
        ) {

            predictionDescription.textContent =
                "CPU usage is expected to increase.";

            predictionStatus.textContent =
                "↗ Increase expected";

        } else if (
            predicted <
            current - 2
        ) {

            predictionDescription.textContent =
                "CPU usage is expected to decrease.";

            predictionStatus.textContent =
                "↘ Decrease expected";

        } else {

            predictionDescription.textContent =
                "CPU usage is expected to remain stable.";

            predictionStatus.textContent =
                "→ Stable usage expected";
        }

    } catch (error) {

        console.error(
            "Prediction error:",
            error
        );
    }
}


/* =========================
   ANOMALY DETECTION
========================= */

async function updateAnomaly() {

    try {

        const response =
            await fetch(
                `${API_BASE}/anomaly`
            );

        const data =
            await response.json();


        if (
            data.status !==
            "success"
        ) {
            return;
        }


        anomalyTitle.textContent =
            data.anomaly
                ? "Anomaly"
                : "Normal";


        anomalyDescription.textContent =
            data.reason ||
            "System metrics are within the learned normal pattern.";


        anomalyStatus.textContent =
            `Severity: ${
                data.severity || "NONE"
            }`;

    } catch (error) {

        console.error(
            "Anomaly error:",
            error
        );
    }
}


/* =========================
   INITIAL LOAD
========================= */

async function loadDashboard() {

    await Promise.all([
        updateSystem(),
        updateChart(),
        updatePrediction(),
        updateAnomaly()
    ]);

    updateTime();
}


/* =========================
   START
========================= */

loadDashboard();


/* =========================
   REAL-TIME UPDATE
========================= */

setInterval(
    updateSystem,
    5000
);

setInterval(
    updateChart,
    5000
);

setInterval(
    updatePrediction,
    5000
);

setInterval(
    updateAnomaly,
    5000
);


/* =========================
   CLOCK
========================= */

setInterval(
    updateTime,
    1000
);


/* =========================
   CHART RANGE
========================= */

if (chartRange) {

    chartRange.addEventListener(
        "change",
        updateChart
    );
}