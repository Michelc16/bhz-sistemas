# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID


def post_init_hook(env):
    admin = env.ref("base.user_admin", raise_if_not_found=False)
    user_root = env["res.users"].browse(SUPERUSER_ID)

    targets = user_root
    if admin:
        targets |= admin

    group_manager = env.ref("bhz_marketplace_core.group_marketplace_manager", raise_if_not_found=False)
    group_seller = env.ref("bhz_marketplace_core.group_marketplace_seller", raise_if_not_found=False)

    for group in (group_manager, group_seller):
        if not group:
            continue
        for user in targets:
            if user not in group.users:
                group.write({"users": [(4, user.id)]})
