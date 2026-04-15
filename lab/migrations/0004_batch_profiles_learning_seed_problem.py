from django.db import migrations, models


def copy_existing_batch_profiles(apps, schema_editor):
    BatchGroup = apps.get_model('lab', 'BatchGroup')
    for group in BatchGroup.objects.all():
        if group.prompt_profile_id:
            group.prompt_profiles.add(group.prompt_profile_id)


class Migration(migrations.Migration):

    dependencies = [
        ('lab', '0003_add_model_selection_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='batchgroup',
            name='prompt_profiles',
            field=models.ManyToManyField(blank=True, related_name='batch_groups_multi', to='lab.promptprofile'),
        ),
        migrations.AddField(
            model_name='learningsession',
            name='seed_problem_text',
            field=models.TextField(default=''),
            preserve_default=False,
        ),
        migrations.RunPython(copy_existing_batch_profiles, migrations.RunPython.noop),
    ]
