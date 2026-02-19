from . import models
from . import controllers
from . import wizard
from . import hooks

# Expose hooks at module level (required by Odoo when referenced in __manifest__.py)
from .hooks import post_init_hook
