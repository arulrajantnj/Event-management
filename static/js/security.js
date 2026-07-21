(function () {
    "use strict";

    const tokenElement = document.querySelector('meta[name="csrf-token"]');
    const csrfToken = tokenElement ? tokenElement.content : "";
    if (!csrfToken) {
        return;
    }

    if (typeof window.fetch === "function") {
        const originalFetch = window.fetch.bind(window);
        window.fetch = function (resource, options) {
            const requestOptions = Object.assign({}, options || {});
            const method = String(requestOptions.method || "GET").toUpperCase();
            const target = resource instanceof Request ? resource.url : String(resource);
            const targetUrl = new URL(target, window.location.href);

            if (targetUrl.origin === window.location.origin && !["GET", "HEAD", "OPTIONS"].includes(method)) {
                const headers = new Headers(requestOptions.headers || (resource instanceof Request ? resource.headers : undefined));
                headers.set("X-CSRFToken", csrfToken);
                requestOptions.headers = headers;
            }

            return originalFetch(resource, requestOptions);
        };
    }

    // jQuery does not use window.fetch, so AJAX forms such as the certificate
    // font uploader need the CSRF header configured separately.
    if (window.jQuery && typeof window.jQuery.ajaxPrefilter === "function") {
        window.jQuery.ajaxPrefilter(function (options, originalOptions, xhr) {
            const method = String(options.type || options.method || "GET").toUpperCase();
            const targetUrl = new URL(options.url || window.location.href, window.location.href);

            if (targetUrl.origin === window.location.origin && !["GET", "HEAD", "OPTIONS"].includes(method)) {
                xhr.setRequestHeader("X-CSRFToken", csrfToken);
            }
        });
    }
})();
