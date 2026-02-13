from . import models
from . import controllers
from . import wizard
from . import hooks

# Expose the hook at the addon package level.
# Odoo's module loader calls: getattr(py_module, post_init_hook)(env)
from .hooks import post_init_hook  # noqa: F401
