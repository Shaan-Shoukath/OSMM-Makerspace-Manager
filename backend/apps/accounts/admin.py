from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as DjangoGroupAdmin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import Group
from unfold.admin import ModelAdmin, TabularInline
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from apps.accounts.models import User
from apps.makerspaces.models import MakerspaceMembership
from config.admin_access import SuperuserOnlyModelAdmin


class MakerspaceMembershipInline(TabularInline):
    model = MakerspaceMembership
    fk_name = "user"
    fields = ("makerspace", "role")
    autocomplete_fields = ("makerspace",)
    extra = 0


@admin.register(User)
class UserAdmin(SuperuserOnlyModelAdmin, DjangoUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    fieldsets = DjangoUserAdmin.fieldsets + (
        (
            "Makerspace Manager Access",
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
    inlines = (MakerspaceMembershipInline,)


admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(SuperuserOnlyModelAdmin, DjangoGroupAdmin, ModelAdmin):
    pass
