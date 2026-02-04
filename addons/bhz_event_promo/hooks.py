from odoo import api, SUPERUSER_ID


def post_init_hook(cr, registry):
    """After install/upgrade, ensure the legacy global 'Agenda' menu is hidden.

    Older versions created website.menu without website_id, making it appear in all websites
    (and auto-appear in new websites). We hide that shared menu and keep per-website menus
    controlled by website.bhz_agenda_enabled.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    # Hide the shared menu created by the XML id (if any)
    try:
        legacy_menu = env.ref("bhz_event_promo.website_menu_guiabh_agenda", raise_if_not_found=False)
    except TypeError:
        legacy_menu = env.ref("bhz_event_promo.website_menu_guiabh_agenda", False)

    if legacy_menu:
        legacy_menu.sudo().write({"active": False})

    # Heuristic: if there is exactly 1 website, keep agenda enabled there (backward compatible).
    websites = env["website"].sudo().search([])
    if len(websites) == 1:
        w = websites[0]
        if not w.bhz_agenda_enabled:
            w.write({"bhz_agenda_enabled": True})
    else:
        # If any website clearly looks like GuiaBH, enable there.
        for w in websites:
            name = (w.name or "").lower()
            domain = (getattr(w, "domain", "") or "").lower()
            if "guiabh" in name or "guia bh" in name or "guiabh" in domain:
                if not w.bhz_agenda_enabled:
                    w.write({"bhz_agenda_enabled": True})
