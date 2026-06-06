import os

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

SITE_NAME = os.environ.get("ADMIN_SITE_NAME", "Makerspace Inventory")


def _can_view_makerspaces(request):
    return request.user.has_perm("makerspaces.view_makerspace")


def _can_view_products(request):
    return request.user.has_perm("inventory.view_inventoryproduct")


def _can_view_users(request):
    return request.user.has_perm("accounts.view_user")


UNFOLD = {
    "SITE_TITLE": SITE_NAME,
    "SITE_HEADER": SITE_NAME,
    "SITE_SYMBOL": "inventory_2",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "THEME": "dark",
    "COLORS": {
        "primary": {
            "50": "245 243 255",
            "100": "237 233 254",
            "200": "221 214 254",
            "300": "196 181 253",
            "400": "167 139 250",
            "500": "139 92 246",
            "600": "124 58 237",
            "700": "109 40 217",
            "800": "91 33 182",
            "900": "76 29 149",
            "950": "46 16 101",
        }
    },
    "SIDEBAR": {
        "show_search": True,
        "navigation": [
            {
                "title": _("Inventory"),
                "separator": True,
                "items": [
                    {
                        "title": _("Makerspaces"),
                        "icon": "store",
                        "link": reverse_lazy("admin:makerspaces_makerspace_changelist"),
                        "permission": _can_view_makerspaces,
                    },
                    {
                        "title": _("Products"),
                        "icon": "inventory_2",
                        "link": reverse_lazy(
                            "admin:inventory_inventoryproduct_changelist"
                        ),
                        "permission": _can_view_products,
                    },
                ],
            },
            {
                "title": _("Accounts"),
                "separator": True,
                "items": [
                    {
                        "title": _("Users"),
                        "icon": "person",
                        "link": reverse_lazy("admin:accounts_user_changelist"),
                        "permission": _can_view_users,
                    }
                ],
            },
        ],
    },
}
