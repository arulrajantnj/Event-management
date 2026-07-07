// ===========================================
// PREVIEW PAGE JAVASCRIPT
// ===========================================

document.addEventListener("DOMContentLoaded", function () {

    console.log("Certificate Preview Loaded");

    // Smooth animation
    document.querySelector(".certificate-card").style.opacity = "0";

    setTimeout(function(){

        document.querySelector(".certificate-card").style.transition="0.8s";
        document.querySelector(".certificate-card").style.opacity="1";

    },200);

});


// ===========================================
// PRINT PREVIEW
// ===========================================

function printCertificate(){

    window.print();

}


// ===========================================
// CONFIRM REGISTRATION
// ===========================================

function confirmRegistration(){

    let ok = confirm(
        "Are you sure?\n\nYour registration will be saved permanently."
    );

    if(ok){

        document.getElementById("confirmForm").submit();

    }

}


// ===========================================
// EDIT DETAILS
// ===========================================

function editDetails(){

    history.back();

}


// ===========================================
// PREVENT DOUBLE SUBMISSION
// ===========================================

document.addEventListener("submit",function(e){

    let btn=e.target.querySelector("button[type='submit']");

    if(btn){

        btn.disabled=true;

        btn.innerHTML="<i class='fa fa-spinner fa-spin'></i> Please Wait...";

    }

});


// ===========================================
// AUTO SCROLL TO CERTIFICATE
// ===========================================

window.onload=function(){

    let preview=document.querySelector(".certificate-card");

    preview.scrollIntoView({

        behavior:"smooth"

    });

}