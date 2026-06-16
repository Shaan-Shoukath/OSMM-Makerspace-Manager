from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("printing", "0005_printrequest_requested_filament_spool_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="printrequestfile",
            name="original_filename",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
    ]
