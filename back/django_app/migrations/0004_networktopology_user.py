# Generated by Django 4.2.7 on 2025-05-05 18:43

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("django_app", "0003_userprofile_user_type_studentgroup_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="networktopology",
            name="user",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="topologies",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
