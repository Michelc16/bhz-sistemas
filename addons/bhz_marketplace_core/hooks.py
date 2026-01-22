# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    admin = env.ref("base.user_admin", raise_if_not_found=False)
    superuser = env["res.users"].browse(SUPERUSER_ID)
    group_manager = env.ref("bhz_marketplace_core.group_marketplace_manager", raise_if_not_found=False)
    group_seller = env.ref("bhz_marketplace_core.group_marketplace_seller", raise_if_not_found=False)

    users = env["res.users"]
    if admin:
        users |= admin
    users |= superuser

    groups = env["res.groups"]
    if group_manager:
        groups |= group_manager
    if group_seller:
        groups |= group_seller

    if users and groups:
        for user in users:
            user.write({"groups_id": [(4, g.id) for g in groups]})
