(function(){
    const eventInput = document.getElementById("attendanceEventId");
    const eventId = eventInput ? eventInput.value : "";

    function postJson(url, payload){
        return fetch(url, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(payload)
        }).then(async response => {
            const data = await response.json();
            data.httpOk = response.ok;
            return data;
        });
    }

    function personHtml(person){
        if (!person) return "";
        const photo = person.photo_url
            ? `<img src="${person.photo_url}" class="attendance-person-photo" alt="">`
            : `<div class="attendance-person-photo bg-light d-flex align-items-center justify-content-center text-muted">No Photo</div>`;
        return `
            <div class="d-flex gap-3 align-items-start flex-wrap">
                ${photo}
                <div class="flex-fill">
                    <h4 class="mb-1">${person.teacher_name || ""}</h4>
                    <div><strong>Registration Number:</strong> <code>${person.reg_id || ""}</code></div>
                    <div><strong>Designation:</strong> ${person.designation || ""}</div>
                    <div><strong>Subject:</strong> ${person.subject || ""}</div>
                    <div><strong>School:</strong> ${person.school_name || ""}</div>
                    <div><strong>Block:</strong> ${person.block || ""}</div>
                    <div><strong>Attendance Status:</strong> ${person.attendance_status || ""}</div>
                    ${person.attendance_time ? `<div><strong>Attendance Time:</strong> ${person.attendance_time}</div>` : ""}
                    ${person.attendance_method ? `<div><strong>Method:</strong> ${person.attendance_method}</div>` : ""}
                </div>
            </div>`;
    }

    function renderScanResult(data){
        const target = document.getElementById("scanResult");
        if (!target) return;
        const duplicate = data.status === "Already Present";
        const ok = data.ok && !duplicate;
        const cls = ok ? "success" : (duplicate ? "warning" : "danger");
        const title = ok ? "Attendance Marked Successfully" : data.message;
        target.className = `attendance-result card ${cls}`;
        target.innerHTML = `
            <div class="card-header ${ok ? "bg-success" : duplicate ? "bg-warning text-dark" : "bg-danger"} text-white">
                ${title}
            </div>
            <div class="card-body">
                ${data.participant ? personHtml(data.participant) : `<div class="h4 text-danger mb-0">${data.message || "Participant Not Found"}</div>`}
            </div>`;

        if (ok && document.getElementById("soundEnabled")?.checked) {
            try {
                const audio = new Audio("data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAACJWAAACABAAZGF0YQAAAAA=");
                audio.play();
            } catch (error) {}
        }
        if (ok && document.getElementById("vibrationEnabled")?.checked && navigator.vibrate) {
            navigator.vibrate(160);
        }
    }

    function initScanner(){
        const reader = document.getElementById("qr-reader");
        if (!reader || typeof Html5Qrcode === "undefined") return;

        const scanner = new Html5Qrcode("qr-reader");
        const cameraSelect = document.getElementById("cameraSelect");
        const startButton = document.getElementById("startScanner");
        const stopButton = document.getElementById("stopScanner");
        let lastScan = "";
        let lastScanAt = 0;

        Html5Qrcode.getCameras().then(cameras => {
            cameraSelect.innerHTML = cameras.map((camera, index) =>
                `<option value="${camera.id}" ${index === cameras.length - 1 ? "selected" : ""}>${camera.label || "Camera " + (index + 1)}</option>`
            ).join("");
        }).catch(() => {
            cameraSelect.innerHTML = `<option value="">Camera permission required</option>`;
        });

        function onScan(decodedText){
            const delay = parseInt(document.getElementById("scanDelay")?.value || "1500", 10);
            const now = Date.now();
            if (decodedText === lastScan && now - lastScanAt < delay) return;
            lastScan = decodedText;
            lastScanAt = now;
            postJson("/api/attendance/scan", {
                scan_text: decodedText,
                event_id: eventId || null
            }).then(renderScanResult);
        }

        startButton?.addEventListener("click", () => {
            const cameraId = cameraSelect.value;
            const config = {fps: 10, qrbox: {width: 260, height: 260}};
            const cameraConfig = cameraId ? {deviceId: {exact: cameraId}} : {facingMode: "environment"};
            scanner.start(cameraConfig, config, onScan).catch(error => {
                renderScanResult({ok:false, message:error && error.message ? error.message : "Unable to start camera"});
            });
        });

        stopButton?.addEventListener("click", () => {
            scanner.stop().catch(() => {});
        });
    }

    function initManual(){
        const input = document.getElementById("manualSearch");
        const button = document.getElementById("manualSearchBtn");
        const results = document.getElementById("manualResults");
        if (!input || !button || !results) return;

        function search(){
            const q = input.value.trim();
            results.innerHTML = `<div class="text-muted">Searching...</div>`;
            fetch(`/api/attendance/search?q=${encodeURIComponent(q)}&event_id=${encodeURIComponent(eventId || "")}`)
                .then(response => response.json())
                .then(data => {
                    if (!data.participants || !data.participants.length) {
                        results.innerHTML = `<div class="alert alert-danger">Participant Not Found</div>`;
                        return;
                    }
                    results.innerHTML = data.participants.map(person => `
                        <div class="col-lg-6">
                            <div class="card manual-result-card">
                                <div class="card-body">
                                    ${personHtml(person)}
                                    <button class="btn btn-success w-100 mt-3 mark-manual" data-id="${person.id}">
                                        <i class="fa-solid fa-user-check"></i> Mark Present
                                    </button>
                                </div>
                            </div>
                        </div>
                    `).join("");
                });
        }

        button.addEventListener("click", search);
        input.addEventListener("keydown", event => {
            if (event.key === "Enter") search();
        });

        results.addEventListener("click", event => {
            const markButton = event.target.closest(".mark-manual");
            if (!markButton) return;
            postJson("/api/attendance/manual", {
                participant_id: markButton.dataset.id
            }).then(data => {
                markButton.closest(".card").outerHTML = `
                    <div class="card attendance-result ${data.status === "Already Present" ? "warning" : "success"}">
                        <div class="card-body">
                            <h5>${data.message}</h5>
                            ${personHtml(data.participant)}
                        </div>
                    </div>`;
            });
        });
    }

    function initCharts(){
        if (typeof Chart === "undefined" || !window.attendanceCharts) return;
        const palette = ["#0d6efd", "#198754", "#ffc107", "#dc3545", "#6f42c1", "#20c997", "#fd7e14", "#0dcaf0"];
        function chart(id, label, data, type){
            const canvas = document.getElementById(id);
            if (!canvas) return;
            new Chart(canvas, {
                type: type || "bar",
                data: {
                    labels: Object.keys(data),
                    datasets: [{label, data: Object.values(data), backgroundColor: palette}]
                },
                options: {responsive: true, maintainAspectRatio: false}
            });
        }
        chart("hourChart", "Attendance by Hour", window.attendanceCharts.hour, "line");
        chart("subjectChart", "Attendance by Subject", window.attendanceCharts.subject, "bar");
        chart("blockChart", "Attendance by Block", window.attendanceCharts.block, "bar");
        chart("schoolChart", "Attendance by School", window.attendanceCharts.school, "bar");
    }

    function initDataTable(){
        if (window.jQuery && jQuery.fn.DataTable && document.getElementById("attendanceTable")) {
            jQuery("#attendanceTable").DataTable({pageLength: 25, order: [[5, "desc"]]});
        }
    }

    document.addEventListener("DOMContentLoaded", function(){
        initScanner();
        initManual();
        initCharts();
        initDataTable();
    });
})();
