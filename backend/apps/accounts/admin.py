from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as DjangoGroupAdmin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import Group
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from apps.accounts.models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    fieldsets = DjangoUserAdmin.fieldsets + (
        (
            "TinkerSpace Access",
            {
                "fields": (
                    "phone",
                    "external_checkin_user_id",
                    "role",
                    "access_status",
                    "restriction_reason",
                ),
            },
        ),
    )
    list_display = ("username", "email", "role", "access_status", "is_staff")
    list_filter = DjangoUserAdmin.list_filter + ("role", "access_status")


admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(DjangoGroupAdmin, ModelAdmin):
    pass
