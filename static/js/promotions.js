document.querySelectorAll('.promotion-slide[data-accent-color]').forEach(function (slide) {
    slide.style.setProperty('--promotion-accent', slide.dataset.accentColor);
});
