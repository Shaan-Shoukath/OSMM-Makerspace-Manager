from django.core.management.base import BaseCommand

from apps.accounts.models import User
from apps.inventory.models import InventoryProduct, PublicAvailabilityMode
from apps.makerspaces.models import Makerspace


class Command(BaseCommand):
    help = "Seed an idempotent demo makerspace and public inventory."

    def handle(self, *args, **options):
        superadmin, user_created = User.objects.get_or_create(
            username="superadmin",
            defaults={
                "email": "superadmin@tinkerspace.local",
                "role": User.Role.SUPERADMIN,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if user_created:
            superadmin.set_unusable_password()
            superadmin.save(update_fields=["password"])

        makerspace, makerspace_created = Makerspace.objects.get_or_create(
            slug="tinkerspace",
            defaults={
                "name": "TinkerSpace",
                "public_inventory_enabled": True,
                "created_by": superadmin,
            },
        )

        products = [
            {
                "name": "Soldering Iron",
                "public_availability_mode": PublicAvailabilityMode.EXACT_COUNT,
                "show_public_count": True,
                "total_quantity": 10,
                "available_quantity": 8,
                "storage_location": "Electronics Bench A",
            },
            {
                "name": "Arduino Uno",
                "public_availability_mode": PublicAvailabilityMode.EXACT_COUNT,
                "show_public_count": False,
                "total_quantity": 20,
                "available_quantity": 2,
            },
            {
                "name": "3D Printer Filament",
                "public_availability_mode": PublicAvailabilityMode.STATUS_ONLY,
                "total_quantity": 50,
                "available_quantity": 50,
                "storage_location": "Fabrication Storage",
            },
            {
                "name": "Oscilloscope",
                "public_availability_mode": PublicAvailabilityMode.STATUS_ONLY,
                "total_quantity": 4,
                "available_quantity": 0,
            },
            {
                "name": "Raspberry Pi 5",
                "public_availability_mode": PublicAvailabilityMode.STATUS_ONLY,
                "total_quantity": 15,
                "available_quantity": 3,
            },
            {
                "name": "Secret Internal Tool",
                "is_public": False,
                "total_quantity": 1,
                "available_quantity": 1,
                "storage_location": "Admin Cabinet",
            },
            {
                "name": "Retired Heat Gun",
                "is_archived": True,
                "is_public": True,
                "total_quantity": 2,
                "available_quantity": 2,
            },
        ]

        created_count = 0
        for product_data in products:
            _, created = InventoryProduct.objects.get_or_create(
                makerspace=makerspace,
                name=product_data["name"],
                defaults=product_data,
            )
            created_count += int(created)

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded demo data: "
                f"user_created={user_created}, "
                f"makerspace_created={makerspace_created}, "
                f"products_created={created_count}."
            )
        )
