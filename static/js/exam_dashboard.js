(function(){
    function initExamCharts(){
        if (typeof Chart === "undefined" || !window.examDashboardCharts) return;

        const palette = [
            "#0d6efd",
            "#198754",
            "#ffc107",
            "#dc3545",
            "#6f42c1",
            "#20c997",
            "#fd7e14",
            "#0dcaf0"
        ];

        function chart(id, label, data, type){
            const canvas = document.getElementById(id);
            if (!canvas) return;

            const values = data || {};
            new Chart(canvas, {
                type: type || "bar",
                data: {
                    labels: Object.keys(values),
                    datasets: [{
                        label: label,
                        data: Object.values(values),
                        backgroundColor: palette,
                        borderColor: palette,
                        borderWidth: 2,
                        tension: .35
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: type === "doughnut"
                        }
                    },
                    scales: type === "doughnut" ? {} : {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                precision: 0
                            }
                        }
                    }
                }
            });
        }

        chart("examStatusChart", "Exam Status", window.examDashboardCharts.status, "doughnut");
        chart("examResultChart", "Results", window.examDashboardCharts.result, "doughnut");
        chart("examSubjectChart", "Attempts by Subject", window.examDashboardCharts.subject, "bar");
        chart("examEventChart", "Attempts by Event", window.examDashboardCharts.event, "bar");
    }

    document.addEventListener("DOMContentLoaded", initExamCharts);
})();
