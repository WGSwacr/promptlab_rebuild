from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lab', '0001_initial'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='difficultypreset',
            unique_together=set(),
        ),
        migrations.AlterModelOptions(
            name='difficultypreset',
            options={'ordering': ('name',)},
        ),
        migrations.RemoveField(
            model_name='difficultypreset',
            name='prompt_profile',
        ),
        migrations.RemoveField(
            model_name='difficultypreset',
            name='is_default',
        ),
        migrations.AlterField(
            model_name='difficultypreset',
            name='name',
            field=models.CharField(max_length=80, unique=True),
        ),
        migrations.AlterUniqueTogether(
            name='stylepreset',
            unique_together=set(),
        ),
        migrations.AlterModelOptions(
            name='stylepreset',
            options={'ordering': ('name',)},
        ),
        migrations.RemoveField(
            model_name='stylepreset',
            name='prompt_profile',
        ),
        migrations.RemoveField(
            model_name='stylepreset',
            name='is_default',
        ),
        migrations.AlterField(
            model_name='stylepreset',
            name='name',
            field=models.CharField(max_length=80, unique=True),
        ),
        migrations.AddField(
            model_name='promptprofile',
            name='difficulty_presets',
            field=models.ManyToManyField(blank=True, related_name='profiles', to='lab.difficultypreset'),
        ),
        migrations.AddField(
            model_name='promptprofile',
            name='style_presets',
            field=models.ManyToManyField(blank=True, related_name='profiles', to='lab.stylepreset'),
        ),
        migrations.AlterField(
            model_name='experimentrun',
            name='effective_style',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
