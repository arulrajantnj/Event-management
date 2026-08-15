document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("student-registration");
    const udiseInput = document.getElementById("udise_no");
    const schoolName = document.getElementById("school_name");
    const status = document.getElementById("school-lookup-status");
    const details = document.getElementById("school-lookup-details");
    const block = document.getElementById("school-block");
    const management = document.getElementById("school-management");

    function setCustomSchoolField(fieldNames, value) {
        const container = fieldNames
            .map((fieldName) => document.querySelector(`[data-registration-field="${fieldName}"]`))
            .find(Boolean);
        const input = container?.querySelector("input:not([type='radio']):not([type='checkbox']), textarea, select");
        if (input) {
            input.value = value || "";
            input.readOnly = true;
        }
    }

    async function lookupSchool() {
        const udiseNo = udiseInput.value.trim();
        if (!/^\d+$/.test(udiseNo)) return;
        status.textContent = "Fetching school details...";
        details.classList.add("d-none");
        try {
            const response = await fetch(`/student/school-lookup/${encodeURIComponent(udiseNo)}`);
            const result = await response.json();
            if (!response.ok) throw new Error(result.error || "School details could not be retrieved.");
            schoolName.value = result.school_name || "";
            schoolName.readOnly = true;
            document.getElementById("school_block").value = result.block || "";
            document.getElementById("school_management").value = result.management || "";
            setCustomSchoolField(["block", "block_name", "school_block"], result.block);
            setCustomSchoolField(["management", "school_management"], result.management);
            block.textContent = `Block: ${result.block || "Not available"}`;
            management.textContent = `Management: ${result.management || "Not available"}`;
            details.classList.remove("d-none");
            status.textContent = "School details fetched successfully.";
        } catch (error) {
            status.textContent = error.message;
        }
    }

    if (udiseInput && schoolName && status && details && block && management) {
        udiseInput.addEventListener("change", lookupSchool);
        udiseInput.addEventListener("blur", lookupSchool);
    }
    if (form) form.addEventListener("submit", () => {
        const button = form.querySelector("button[type='submit']");
        if (button) { button.disabled = true; button.textContent = "Submitting..."; }
    });
});
