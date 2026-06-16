from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("boxes", "0007_alter_qrscanevent_context"),
        ("hardware_requests", "0012_hardwarerequestitem_needs_fix_quantity"),
    ]

    operations = [
        migrations.AddField(
            model_name="publictoolloan",
            name="container",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="boxes.box",
            ),
        ),
        migrations.AddConstraint(
            model_name="publictoolloan",
            constraint=models.UniqueConstraint(
                condition=models.Q(status="checked_out"),
                fields=("container",),
                name="uniq_active_loan_per_container",
            ),
        ),
    ]
