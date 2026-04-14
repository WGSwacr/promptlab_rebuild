from django.contrib import admin

from .models import (
    BatchGroup,
    DifficultyPreset,
    EvaluationReview,
    ExperimentRun,
    LearningSession,
    LearningTurn,
    PromptProfile,
    Questionnaire,
    StylePreset,
    SystemPrompt,
    TaskInstruction,
    TurnGrade,
)


@admin.register(PromptProfile)
class PromptProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'system_prompt', 'task_instruction', 'created_at', 'updated_at')
    filter_horizontal = ('difficulty_presets', 'style_presets')


@admin.register(ExperimentRun)
class ExperimentRunAdmin(admin.ModelAdmin):
    list_display = ('name', 'prompt_profile', 'run_type', 'parse_success', 'response_time_ms', 'created_at')
    list_filter = ('run_type', 'parse_success')


@admin.register(BatchGroup)
class BatchGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'prompt_profile', 'repetitions', 'status', 'created_at', 'completed_at')
    list_filter = ('status',)


@admin.register(LearningSession)
class LearningSessionAdmin(admin.ModelAdmin):
    list_display = ('participant_code', 'prompt_profile', 'target_turns', 'status', 'created_at', 'completed_at')
    list_filter = ('status',)


admin.site.register(SystemPrompt)
admin.site.register(TaskInstruction)
admin.site.register(DifficultyPreset)
admin.site.register(StylePreset)
admin.site.register(EvaluationReview)
admin.site.register(LearningTurn)
admin.site.register(TurnGrade)
admin.site.register(Questionnaire)
