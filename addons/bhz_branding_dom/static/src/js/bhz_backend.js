odoo.define('bhz_branding_dom.backend', function (require) {
    "use strict";

    const domReady = require('web.dom_ready');

    domReady(function () {
        // 1) título da aba
        document.title = "BHZ SISTEMAS";

        // 2) favicon
        const bhzFavicon = '/bhz_branding_dom/static/src/img/favicon.ico';
        let link = document.querySelector("link[rel~='icon']");
        if (!link) {
            link = document.createElement('link');
            link.rel = 'icon';
            document.head.appendChild(link);
        }
        link.href = bhzFavicon;

        // 3) logo na navbar do backend
        const navbarBrand = document.querySelector('.o_main_navbar .o_navbar_brand, .o_main_navbar .o_menu_brand');
        if (navbarBrand) {
            navbarBrand.style.backgroundImage = "url('/bhz_branding_dom/static/src/img/bhz_logo.png')";
            navbarBrand.style.backgroundRepeat = "no-repeat";
            navbarBrand.style.backgroundSize = "contain";
            navbarBrand.style.width = "170px";
            navbarBrand.style.textIndent = "-9999px";  // esconde texto
            navbarBrand.textContent = "BHZ SISTEMAS";
        }
    });
});
