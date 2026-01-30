"""Models loaded by this module.

We load only what is strictly necessary for the feature set used on the
website (event helpers / routes).

We deliberately avoid extending `website.website` and `res.config.settings`
because those add SQL columns and can break the instance if code is deployed
without a module upgrade.
"""

from . import event
