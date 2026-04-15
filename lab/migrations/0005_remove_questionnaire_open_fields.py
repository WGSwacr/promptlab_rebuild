from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('lab', '0004_batch_profiles_learning_seed_problem'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='questionnaire',
            name='open_helpful_part',
        ),
        migrations.RemoveField(
            model_name='questionnaire',
            name='open_problem_encountered',
        ),
        migrations.RemoveField(
            model_name='questionnaire',
            name='open_suggestion',
        ),
    ]
