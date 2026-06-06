from django.urls import path

from apps.inventory.views import PublicInventoryListView, PublicMakerspaceListView

urlpatterns = [
    path(
        "public/makerspaces/",
        PublicMakerspaceListView.as_view(),
        name="public-makerspaces",
    ),
    path(
        "public/<slug:makerspace_slug>/inventory/",
        PublicInventoryListView.as_view(),
        name="public-inventory",
    ),
]
