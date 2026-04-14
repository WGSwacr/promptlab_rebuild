from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lab', '0002_align_preset_schema'),
    ]

    operations = [
        migrations.AddField(
            model_name='batchgroup',
            name='selected_model',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='batchgroup',
            name='actual_model',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='experimentrun',
            name='requested_model',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='experimentrun',
            name='actual_model',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='learningsession',
            name='selected_model',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='learningsession',
            name='actual_model',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='learningturn',
            name='model_used',
            field=models.CharField(blank=True, max_length=200),
        ),
    ]
