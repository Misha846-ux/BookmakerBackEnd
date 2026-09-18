from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bmApp', '0009_merge_20260918_1239'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userentity',
            name='phone',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AlterField(
            model_name='userentity',
            name='photo',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
    ]
