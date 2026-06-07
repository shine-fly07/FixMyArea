document.addEventListener("DOMContentLoaded", () => {
    const body = document.body;
    const darkMode = localStorage.getItem("fixmyarea-dark-mode") === "true";
    if (darkMode) body.classList.add("dark-mode");

    document.getElementById("darkModeToggle")?.addEventListener("click", () => {
        body.classList.toggle("dark-mode");
        localStorage.setItem("fixmyarea-dark-mode", body.classList.contains("dark-mode"));
    });

    document.getElementById("sidebarToggle")?.addEventListener("click", () => {
        body.classList.toggle("sidebar-open");
    });

    document.querySelectorAll("input[type='file'][data-preview]").forEach((input) => {
        input.addEventListener("change", () => {
            const target = document.querySelector(input.dataset.preview);
            const file = input.files?.[0];
            if (!target || !file) return;
            target.src = URL.createObjectURL(file);
            target.style.display = "block";
        });
    });

    document.querySelectorAll("form[data-confirm]").forEach((form) => {
        form.addEventListener("submit", (event) => {
            if (!confirm(form.dataset.confirm)) event.preventDefault();
        });
    });

    document.querySelectorAll(".data-table").forEach((table) => {
        const input = document.createElement("input");
        input.className = "form-control form-control-sm mb-3";
        input.placeholder = "Quick search table";
        table.closest(".table-responsive")?.before(input);
        input.addEventListener("input", () => {
            const term = input.value.toLowerCase();
            table.querySelectorAll("tbody tr").forEach((row) => {
                row.style.display = row.textContent.toLowerCase().includes(term) ? "" : "none";
            });
        });
    });

    const palette = ["#2364aa", "#2a9d8f", "#e9c46a", "#f4a261", "#e76f51", "#6d5dfc", "#4a5568"];
    const parseData = (id) => {
        const canvas = document.getElementById(id);
        if (!canvas) return null;
        const rows = JSON.parse(canvas.dataset.chart || "[]");
        return { canvas, labels: rows.map((row) => row.label), values: rows.map((row) => row.value) };
    };
    const makeChart = (id, type, label) => {
        const data = parseData(id);
        if (!data || !window.Chart) return;
        new Chart(data.canvas, {
            type,
            data: {
                labels: data.labels,
                datasets: [{
                    label,
                    data: data.values,
                    backgroundColor: type === "line" ? "rgba(35,100,170,.18)" : palette,
                    borderColor: "#2364aa",
                    borderWidth: 2,
                    tension: .35,
                    fill: type === "line"
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: type !== "bar" && type !== "line" } },
                scales: type === "pie" || type === "doughnut" ? {} : { y: { beginAtZero: true, ticks: { precision: 0 } } }
            }
        });
    };

    makeChart("categoryChart", "pie", "Categories");
    makeChart("statusChart", "bar", "Statuses");
    makeChart("reportedChart", "line", "Reported");
    makeChart("priorityChart", "doughnut", "Priorities");
    makeChart("resolutionChart", "doughnut", "Resolution Rate");
});
