odoo.define('bhz_branding_dom.website', function (require) {
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

        // 3) tentar colocar logo no header do site
        const header = document.querySelector('header, .o_header_standard, .o_header');
        if (header) {
            // se já tiver img, troca
            const existingLogo = header.querySelector('img');
            if (existingLogo) {
                existingLogo.src = '/bhz_branding_dom/static/src/img/bhz_logo.png';
                existingLogo.alt = 'BHZ SISTEMAS';
            } else {
                const div = document.createElement('div');
                div.style.padding = '0.5rem 1rem';
                const a = document.createElement('a');
                a.href = '/';
                const img = document.createElement('img');
                img.src = '/bhz_branding_dom/static/src/img/bhz_logo.png';
                img.alt = 'BHZ SISTEMAS';
                img.style.height = '40px';
                a.appendChild(img);
                div.appendChild(a);
                header.prepend(div);
            }
        }

        // 4) rodapé BHZ (mesmo se o tema não tiver brand view)
        let footer = document.querySelector('footer');
        if (!footer) {
            footer = document.createElement('footer');
            document.body.appendChild(footer);
        }
        const bhzFoot = document.createElement('div');
        bhzFoot.className = 'bhz-footer-branding';
        bhzFoot.textContent = 'Sistema personalizado por BHZ SISTEMAS';
        footer.appendChild(bhzFoot);
    });
});
