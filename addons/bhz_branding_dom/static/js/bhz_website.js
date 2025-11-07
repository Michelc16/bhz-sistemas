odoo.define('bhz_branding_dom.website', function (require) {
    "use strict";

    const publicRoot = require('web.dom_ready');

    publicRoot(function () {
        // 1) título
        document.title = "BHZ SISTEMAS";

        // 2) favicon (mesma lógica do backend)
        const bhzFavicon = '/bhz_branding_dom/static/src/img/favicon.ico';
        let link = document.querySelector("link[rel~='icon']");
        if (!link) {
            link = document.createElement('link');
            link.rel = 'icon';
            document.head.appendChild(link);
        }
        link.href = bhzFavicon;

        // 3) tentar colocar logo no header
        // tenta pegar o primeiro header do site
        const header = document.querySelector('header, .o_header_standard, .o_header');
        if (header) {
            // verifica se já tem um logo
            let logo = header.querySelector('img');
            if (!logo) {
                // cria um bloco de logo
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
            } else {
                // se já tem logo, troca pela sua
                logo.src = '/bhz_branding_dom/static/src/img/bhz_logo.png';
                logo.alt = 'BHZ SISTEMAS';
            }
        }

        // 4) inserir rodapé BHZ mesmo que o tema não tenha a view de brand
        let footer = document.querySelector('footer');
        if (!footer) {
            footer = document.createElement('footer');
            document.body.appendChild(footer);
        }
        const bhzFoot = document.createElement('div');
        bhzFoot.className = 'bhz-footer-branding';
        bhzFoot.style.fontSize = '0.75rem';
        bhzFoot.style.color = '#666';
        bhzFoot.style.marginTop = '1rem';
        bhzFoot.style.padding = '0.5rem 1rem';
        bhzFoot.textContent = 'Sistema personalizado por BHZ SISTEMAS';
        footer.appendChild(bhzFoot);
    });
});
