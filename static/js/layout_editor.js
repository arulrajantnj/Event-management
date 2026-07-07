$(document).ready(function () {

    let selectedField = null;
    let fieldsState = {};

    let templateId = $("#certificateCanvas").data("template");

    // =========================
    // INIT LOAD
    // =========================
    loadLayout();

    // =========================
    // FIELD SELECT
    // =========================
    $(document).on("click", ".draggable-field", function () {

        $(".draggable-field").removeClass("selected");

        $(this).addClass("selected");

        selectedField = $(this);

        $("#fontSize").val(parseInt($(this).css("font-size")));
        $("#fontColor").val(rgbToHex($(this).css("color")));
    });

    // =========================
    // DRAG + RESIZE
    // =========================
    function makeInteractive() {

        $(".draggable-field").draggable({
            containment: "#certificateCanvas",
            stop: function () {
                updateState($(this));
            }
        });

        $(".photo-box, .qr-box").resizable({
            containment: "#certificateCanvas",
            stop: function () {
                updateState($(this));
            }
        });
    }

    // =========================
    // UPDATE STATE
    // =========================
    function updateState(el) {

        let id = el.attr("id");

        fieldsState[id] = {
            field_name: id,
            x: el.position().left,
            y: el.position().top,
            width: el.outerWidth(),
            height: el.outerHeight(),
            font_size: parseInt(el.css("font-size")),
            font_family: el.css("font-family"),
            font_color: rgbToHex(el.css("color")),
            font_weight: el.css("font-weight"),
            text_align: el.css("text-align"),
            shape:
                el.hasClass("oval") ? "oval" :
                el.hasClass("circle") ? "circle" :
                el.hasClass("rounded-photo") ? "rounded" :
                "rectangle",
            rotation: 0,
            visible: true
        };
    }

    // =========================
    // FONT SIZE CHANGE
    // =========================
    $("#fontSize").on("input", function () {

        if (selectedField) {

            selectedField.css("font-size", $(this).val() + "px");

            updateState(selectedField);
        }
    });

    // =========================
    // FONT COLOR CHANGE
    // =========================
    $("#fontColor").change(function () {

        if (selectedField) {

            selectedField.css("color", $(this).val());

            updateState(selectedField);
        }
    });

    // =========================
    // PHOTO SHAPE
    // =========================
    $("#photoShape").change(function () {

        $("#teacher_photo").removeClass("oval circle rounded-photo");

        let shape = $(this).val();

        if (shape === "oval") $("#teacher_photo").addClass("oval");
        else if (shape === "circle") $("#teacher_photo").addClass("circle");
        else if (shape === "rounded") $("#teacher_photo").addClass("rounded-photo");

        updateState($("#teacher_photo"));
    });

    // =========================
    // SAVE LAYOUT (FIXED)
    // =========================
    $("#saveLayout").click(function () {

        let payload = {
            template_id: templateId,
            fields: Object.values(fieldsState)
        };

        $.ajax({
            url: "/api/save-layout",
            method: "POST",
            contentType: "application/json",
            data: JSON.stringify(payload),
            success: function () {
                alert("Layout Saved Successfully");
            },
            error: function () {
                alert("Save Failed");
            }
        });
    });

    // =========================
    // LOAD LAYOUT
    // =========================
    function loadLayout() {

        $.get("/api/layout/" + templateId, function (fields) {

            fields.forEach(function (item) {

                let obj = $("#" + item.field_name);

                obj.data("id", item.id);

                obj.css({
                    left: item.x + "px",
                    top: item.y + "px",
                    width: item.width + "px",
                    height: item.height + "px",
                    fontSize: item.font_size + "px",
                    fontFamily: item.font_family,
                    color: item.font_color,
                    fontWeight: item.font_weight,
                    textAlign: item.text_align
                });

                if (item.shape === "oval") obj.addClass("oval");
                if (item.shape === "circle") obj.addClass("circle");
                if (item.shape === "rounded") obj.addClass("rounded-photo");

                updateState(obj);
            });

            makeInteractive();
        });
    }

    // =========================
    // RGB TO HEX
    // =========================
    function rgbToHex(rgb) {

        if (!rgb || !rgb.startsWith("rgb")) return rgb;

        let nums = rgb.match(/\d+/g);

        return (
            "#" +
            nums.slice(0, 3).map(x =>
                ("0" + parseInt(x).toString(16)).slice(-2)
            ).join("")
        );
    }

});