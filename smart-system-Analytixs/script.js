let cpu = 42;
let memory = 61;
let disk = 68;
let network = 24;

const cpuText = document.getElementById("cpu");
const memoryText = document.getElementById("memory");
const diskText = document.getElementById("disk");
const networkText = document.getElementById("network");

const cpuBar = document.getElementById("cpuBar");
const memoryBar = document.getElementById("memoryBar");
const diskBar = document.getElementById("diskBar");

const timeText = document.getElementById("time");


/* CHART */

const ctx = document.getElementById("cpuChart");

const labels = [
    "10:00",
    "10:05",
    "10:10",
    "10:15",
    "10:20",
    "10:25",
    "10:30",
    "Now"
];

const values = [
    35,
    48,
    43,
    58,
    45,
    52,
    40,
    42
];


const cpuChart = new Chart(ctx, {

    type: "line",

    data: {

        labels: labels,

        datasets: [

            {
                label: "CPU Usage",

                data: values,

                borderColor: "#4f46e5",

                backgroundColor: "rgba(79,70,229,0.08)",

                borderWidth: 3,

                fill: true,

                tension: 0.4,

                pointRadius: 3,

                pointBackgroundColor: "#4f46e5"
            }

        ]

    },

    options: {

        responsive: true,

        maintainAspectRatio: false,

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

                    callback: function(value) {
                        return value + "%";
                    }

                }

            }

        }

    }

});


/* UPDATE DASHBOARD */

function updateDashboard() {

    cpu = Math.floor(Math.random() * 35) + 35;

    memory = Math.floor(Math.random() * 25) + 45;

    disk = Math.floor(Math.random() * 10) + 65;

    network = Math.floor(Math.random() * 20) + 15;


    cpuText.textContent = cpu + "%";

    memoryText.textContent = memory + "%";

    diskText.textContent = disk + "%";

    networkText.textContent = network + " MB/s";


    cpuBar.style.width = cpu + "%";

    memoryBar.style.width = memory + "%";

    diskBar.style.width = disk + "%";


    const now = new Date();

    timeText.textContent =
        now.getHours().toString().padStart(2, "0") +
        ":" +
        now.getMinutes().toString().padStart(2, "0") +
        ":" +
        now.getSeconds().toString().padStart(2, "0");


    /* Update chart */

    cpuChart.data.labels.push("Now");

    cpuChart.data.datasets[0].data.push(cpu);


    if (cpuChart.data.labels.length > 12) {

        cpuChart.data.labels.shift();

        cpuChart.data.datasets[0].data.shift();

    }


    cpuChart.update();

}


/* Every 2 seconds */

setInterval(updateDashboard, 2000);