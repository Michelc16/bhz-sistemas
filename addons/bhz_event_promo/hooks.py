def _set_menu_visibility(env, menu, visible):
    Menu = env["website.menu"]
    # Odoo 19 removed "active" on website.menu. Prefer supported visibility fields.
    for field in ("is_visible", "is_published", "website_published", "active"):
        if field in Menu._fields:
            menu.sudo().write({field: bool(visible)})
            return
    if not visible:
        menu.sudo().unlink()


def post_init_hook(env):
    """After install/upgrade, ensure the legacy global 'Agenda' menu is hidden.

    Older versions created website.menu without website_id, making it appear in all websites
    (and auto-appear in new websites). We hide that shared menu and keep per-website menus
    controlled by website.bhz_agenda_enabled.
    """
    # Hide the shared menu created by the XML id (if any)
    try:
        legacy_menu = env.ref("bhz_event_promo.website_menu_guiabh_agenda", raise_if_not_found=False)
    except TypeError:
        legacy_menu = env.ref("bhz_event_promo.website_menu_guiabh_agenda", False)

    if legacy_menu:
        _set_menu_visibility(env, legacy_menu, False)

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
