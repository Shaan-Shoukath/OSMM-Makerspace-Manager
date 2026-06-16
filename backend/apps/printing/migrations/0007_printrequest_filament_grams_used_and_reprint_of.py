from django.db import migrations, models
import django.db.models.deletion


def forwards(apps, schema_editor):
    from django.db.models import F

    PrintRequest = apps.get_model("printing", "PrintRequest")
    PrintRequest.objects.filter(
        status="completed",
        estimated_filament_grams__isnull=False,
    ).update(filament_grams_used=F("estimated_filament_grams"))


class Migration(migrations.Migration):

    dependencies = [
        ("printing", "0006_printrequestfile_original_filename"),
    ]

    operations = [
        migrations.AddField(
            model_name="printrequest",
            name="filament_grams_used",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=8),
        ),
        migrations.AddField(
            model_name="printrequest",
            name="reprint_of",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="reprints",
                to="printing.printrequest",
            ),
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
