(function () {
    "use strict";

    // roda quando o DOM estiver pronto
    function applyBranding() {
        try {
            // título da janela
            document.title = 'BHZ SISTEMAS';

            // trocar favicon
            var link = document.querySelector("link[rel*='icon']") || document.createElement('link');
            link.type = 'image/x-icon';
            link.rel = 'shortcut icon';
            // caminho do favicon no módulo
            link.href = '/bhz_branding_dom/static/src/img/favicon.ico';
            document.getElementsByTagName('head')[0].appendChild(link);

            // tenta injetar um título no header ao lado do menu (se existir)
            var navbar = document.querySelector('.o_main_navbar') || document.querySelector('.o_navbar');
            if (navbar) {
                if (!document.querySelector('.bhz-header-title')) {
                    var span = document.createElement('span');
                    span.className = 'bhz-header-title';
                    span.innerText = 'BHZ SISTEMAS';
                    // insere no começo
                    navbar.insertBefore(span, navbar.firstChild);
                }
            }
        } catch (e) {
            console.error('BHZ branding script error', e);
        }
    }

    // executar após carregamento (tenta várias vezes porque Odoo carrega dinamicamente)
    function readyLoop(count) {
        if (count === undefined) { count = 0; }
        applyBranding();
        if (count < 15) {
            setTimeout(function () { readyLoop(count + 1); }, 600);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            readyLoop(0);
        });
    } else {
        readyLoop(0);
    }
})();
