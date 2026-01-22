# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID


def post_init_hook(env):
    admin = env.ref("base.user_admin", raise_if_not_found=False)
    root = env["res.users"].browse(SUPERUSER_ID)

    targets = root
    if admin:
        targets |= admin

    group_internal = env.ref("base.group_user", raise_if_not_found=False)
    group_portal = env.ref("base.group_portal", raise_if_not_found=False)
    group_manager = env.ref("bhz_marketplace_core.group_marketplace_manager", raise_if_not_found=False)
    group_seller = env.ref("bhz_marketplace_core.group_marketplace_seller", raise_if_not_found=False)

    def _write_users(group, users, mode):
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
            if mode == "add" and u not in current:
                group.write({field: [(4, u.id)]})
            if mode == "remove" and u in current:
                group.write({field: [(3, u.id)]})

    # Garantir que sejam usuários internos e não portal
    if group_portal:
        _write_users(group_portal, targets, "remove")
    if group_internal:
        _write_users(group_internal, targets, "add")

    _write_users(group_seller, targets, "add")
    _write_users(group_manager, targets, "add")
