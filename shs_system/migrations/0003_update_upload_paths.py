from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("shs_system", "0002_fix_schoolinformation_media_paths"),
    ]

    operations = [
        migrations.AlterField(
            model_name="schoolauthoritysignature",
            name="signature",
            field=models.ImageField(upload_to="signatures/"),
        ),
        migrations.AlterField(
            model_name="schoolinformation",
            name="logo",
            field=models.ImageField(blank=True, null=True, upload_to="school_image/"),
        ),
        migrations.AlterField(
            model_name="schoolinformation",
            name="school_stamp",
            field=models.ImageField(blank=True, null=True, upload_to="school_image/"),
        ),
    ]





