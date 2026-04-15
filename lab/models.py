from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


LIKERT_VALIDATORS = [MinValueValidator(1), MaxValueValidator(5)]


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SystemPrompt(models.Model):
    name = models.CharField(max_length=100, unique=True)
    text = models.TextField()

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name


class TaskInstruction(models.Model):
    name = models.CharField(max_length=100, unique=True)
    text = models.TextField()

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name


class DifficultyPreset(models.Model):
    name = models.CharField(max_length=80, unique=True)
    description = models.CharField(max_length=255, blank=True)
    instruction_text = models.TextField()

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name


class StylePreset(models.Model):
    name = models.CharField(max_length=80, unique=True)
    description = models.CharField(max_length=255, blank=True)
    instruction_text = models.TextField()

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name


class PromptProfile(TimestampedModel):
    name = models.CharField(max_length=120, unique=True)
    description = models.CharField(max_length=255, blank=True)
    system_prompt = models.ForeignKey(SystemPrompt, on_delete=models.PROTECT, related_name='profiles')
    task_instruction = models.ForeignKey(TaskInstruction, on_delete=models.PROTECT, related_name='profiles')
    curriculum_text = models.TextField()
    seed_problem_text = models.TextField()
    baseline_text = models.TextField(blank=True)
    difficulty_presets = models.ManyToManyField(DifficultyPreset, blank=True, related_name='profiles')
    style_presets = models.ManyToManyField(StylePreset, blank=True, related_name='profiles')

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name

    @property
    def difficulty_names(self):
        return list(self.difficulty_presets.values_list('name', flat=True))

    @property
    def style_names(self):
        return list(self.style_presets.values_list('name', flat=True))


class BatchGroup(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_RUNNING = 'running'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_RUNNING, 'Running'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED, 'Failed'),
    ]

    name = models.CharField(max_length=120)
    prompt_profile = models.ForeignKey(PromptProfile, on_delete=models.CASCADE, related_name='batch_groups')
    prompt_profiles = models.ManyToManyField(PromptProfile, blank=True, related_name='batch_groups_multi')
    selected_model = models.CharField(max_length=200, blank=True)
    actual_model = models.CharField(max_length=200, blank=True)
    seed_problem_override = models.TextField(blank=True)
    baseline_override = models.TextField(blank=True)
    repetitions = models.PositiveIntegerField(default=3)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return self.name


class ExperimentRun(models.Model):
    RUN_SINGLE = 'single'
    RUN_BATCH = 'batch'
    RUN_TYPES = [
        (RUN_SINGLE, 'Single'),
        (RUN_BATCH, 'Batch'),
    ]

    name = models.CharField(max_length=120)
    prompt_profile = models.ForeignKey(PromptProfile, on_delete=models.CASCADE, related_name='experiment_runs')
    run_type = models.CharField(max_length=20, choices=RUN_TYPES, default=RUN_SINGLE)
    batch_group = models.ForeignKey(BatchGroup, on_delete=models.CASCADE, null=True, blank=True, related_name='runs')
    seed_problem_override = models.TextField(blank=True)
    baseline_override = models.TextField(blank=True)
    requested_model = models.CharField(max_length=200, blank=True)
    actual_model = models.CharField(max_length=200, blank=True)
    effective_seed_problem = models.TextField(blank=True)
    effective_baseline = models.TextField(blank=True)
    effective_difficulty = models.CharField(max_length=80, blank=True)
    effective_style = models.CharField(max_length=255, blank=True)
    assembled_prompt = models.TextField(blank=True)
    raw_response = models.TextField(blank=True)
    structured_output = models.JSONField(default=dict, blank=True)
    parse_success = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    response_time_ms = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f'{self.name} ({self.run_type})'


class EvaluationReview(models.Model):
    experiment_run = models.ForeignKey(ExperimentRun, on_delete=models.CASCADE, related_name='reviews')
    reviewer_name = models.CharField(max_length=100)
    knowledge_alignment = models.PositiveSmallIntegerField(validators=LIKERT_VALIDATORS)
    difficulty_appropriateness = models.PositiveSmallIntegerField(validators=LIKERT_VALIDATORS)
    structural_completeness = models.PositiveSmallIntegerField(validators=LIKERT_VALIDATORS)
    novelty = models.PositiveSmallIntegerField(validators=LIKERT_VALIDATORS)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f'Review for {self.experiment_run.name} by {self.reviewer_name}'


class LearningSession(models.Model):
    STATUS_ACTIVE = 'active'
    STATUS_COMPLETED = 'completed'
    STATUS_ABANDONED = 'abandoned'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_ABANDONED, 'Abandoned'),
    ]

    participant_code = models.CharField(max_length=50)
    prompt_profile = models.ForeignKey(PromptProfile, on_delete=models.CASCADE, related_name='learning_sessions')
    selected_model = models.CharField(max_length=200, blank=True)
    actual_model = models.CharField(max_length=200, blank=True)
    seed_problem_text = models.TextField()
    target_turns = models.PositiveIntegerField(default=5)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f'{self.participant_code} / {self.prompt_profile.name}'

    @property
    def completed_turns(self):
        return self.turns.count()


class LearningTurn(models.Model):
    RESULT_PENDING = 'pending'
    RESULT_CORRECT = 'correct'
    RESULT_PARTIAL = 'partial'
    RESULT_INCORRECT = 'incorrect'
    RESULT_CHOICES = [
        (RESULT_PENDING, 'Pending'),
        (RESULT_CORRECT, 'Correct'),
        (RESULT_PARTIAL, 'Partially Correct'),
        (RESULT_INCORRECT, 'Incorrect'),
    ]

    ACTION_KEEP = 'keep'
    ACTION_EASY = 'easy'
    ACTION_MEDIUM = 'medium'
    ACTION_HARD = 'hard'
    ACTION_END = 'end'
    ACTION_CHOICES = [
        (ACTION_KEEP, 'Keep current level'),
        (ACTION_EASY, 'Generate easy follow-up'),
        (ACTION_MEDIUM, 'Generate medium follow-up'),
        (ACTION_HARD, 'Generate hard follow-up'),
        (ACTION_END, 'End session'),
    ]

    learning_session = models.ForeignKey(LearningSession, on_delete=models.CASCADE, related_name='turns')
    round_number = models.PositiveIntegerField()
    generated_focus = models.CharField(max_length=150, blank=True)
    generated_question = models.TextField()
    model_used = models.CharField(max_length=200, blank=True)
    learner_answer = models.TextField(blank=True)
    difficulty_used = models.CharField(max_length=20, blank=True)
    correct_count = models.PositiveIntegerField(default=0)
    total_count = models.PositiveIntegerField(default=0)
    accuracy_ratio = models.FloatField(default=0.0)
    result_label = models.CharField(max_length=20, choices=RESULT_CHOICES, default=RESULT_PENDING)
    system_action = models.CharField(max_length=20, choices=ACTION_CHOICES, default=ACTION_KEEP)
    question_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('round_number', 'created_at')
        unique_together = ('learning_session', 'round_number')

    def __str__(self):
        return f'{self.learning_session} / round {self.round_number}'


class TurnGrade(models.Model):
    learning_turn = models.ForeignKey(LearningTurn, on_delete=models.CASCADE, related_name='grades')
    case_order = models.PositiveIntegerField(default=1)
    test_input = models.TextField(blank=True)
    expected_output = models.TextField(blank=True)
    learner_output = models.TextField(blank=True)
    is_correct = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ('case_order', 'id')

    def __str__(self):
        return f'{self.learning_turn} / case {self.case_order}'


class Questionnaire(models.Model):
    session = models.OneToOneField(LearningSession, on_delete=models.CASCADE, related_name='questionnaire')
    q1_topic_relevance = models.PositiveSmallIntegerField(validators=LIKERT_VALIDATORS)
    q2_difficulty_appropriateness = models.PositiveSmallIntegerField(validators=LIKERT_VALIDATORS)
    q3_clarity = models.PositiveSmallIntegerField(validators=LIKERT_VALIDATORS)
    q4_adaptive_followup = models.PositiveSmallIntegerField(validators=LIKERT_VALIDATORS)
    q5_step_by_step_support = models.PositiveSmallIntegerField(validators=LIKERT_VALIDATORS)
    q6_weak_point_identification = models.PositiveSmallIntegerField(validators=LIKERT_VALIDATORS)
    q7_ease_of_interaction = models.PositiveSmallIntegerField(validators=LIKERT_VALIDATORS)
    q8_readability = models.PositiveSmallIntegerField(validators=LIKERT_VALIDATORS)
    q9_willingness_to_reuse = models.PositiveSmallIntegerField(validators=LIKERT_VALIDATORS)
    q10_overall_helpfulness = models.PositiveSmallIntegerField(validators=LIKERT_VALIDATORS)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f'Questionnaire for {self.session}'
