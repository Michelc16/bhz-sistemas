# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID


def post_init_hook(env):
    admin = env.ref("base.user_admin", raise_if_not_found=False)
    root = env["res.users"].browse(SUPERUSER_ID)

    targets = root
    if admin:
        targets |= admin

    group_manager = env.ref("bhz_marketplace_core.group_marketplace_manager", raise_if_not_found=False)
    group_seller = env.ref("bhz_marketplace_core.group_marketplace_seller", raise_if_not_found=False)

    def _add_users_to_group(group, users):
        if not group:
            return
        if "users_ids" in group._fields:
            field = "users_ids"
        elif "user_ids" in group._fields:
            field = "user_ids"
        else:
            raise RuntimeError("res.groups não possui users_ids/user_ids nesta versão; ajustar hook para usar o campo correto.")

        for u in users:
            current = group[field]
            if u not in current:
                group.write({field: [(4, u.id)]})

    _add_users_to_group(group_seller, targets)
    _add_users_to_group(group_manager, targets)
