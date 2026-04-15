from django import forms

from .services.model_catalog import get_model_choice_options
from .models import (
    BatchGroup,
    DifficultyPreset,
    EvaluationReview,
    LearningSession,
    LearningTurn,
    PromptProfile,
    Questionnaire,
    StylePreset,
    SystemPrompt,
    TaskInstruction,
)


class PromptProfileForm(forms.ModelForm):
    class Meta:
        model = PromptProfile
        fields = [
            'name',
            'description',
            'system_prompt',
            'task_instruction',
            'curriculum_text',
            'seed_problem_text',
            'baseline_text',
            'difficulty_presets',
            'style_presets',
        ]
        widgets = {
            'description': forms.TextInput(attrs={'placeholder': 'Short description'}),
            'curriculum_text': forms.Textarea(attrs={'rows': 6}),
            'seed_problem_text': forms.Textarea(attrs={'rows': 8}),
            'baseline_text': forms.Textarea(attrs={'rows': 8}),
            'difficulty_presets': forms.SelectMultiple(attrs={'size': 6}),
            'style_presets': forms.SelectMultiple(attrs={'size': 6}),
        }
        help_texts = {
            'difficulty_presets': 'Select one or more difficulty presets. Run Lab and Batch Lab will randomly choose one of the selected presets.',
            'style_presets': 'Select one or more style presets. All selected styles will be applied together during generation.',
        }


class SystemPromptCreateForm(forms.ModelForm):
    class Meta:
        model = SystemPrompt
        fields = ['name', 'text']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 6}),
        }


class TaskInstructionCreateForm(forms.ModelForm):
    class Meta:
        model = TaskInstruction
        fields = ['name', 'text']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 6}),
        }


class DifficultyPresetCreateForm(forms.ModelForm):
    class Meta:
        model = DifficultyPreset
        fields = ['name', 'description', 'instruction_text']
        widgets = {
            'description': forms.TextInput(attrs={'placeholder': 'Short description'}),
            'instruction_text': forms.Textarea(attrs={'rows': 5}),
        }


class StylePresetCreateForm(forms.ModelForm):
    class Meta:
        model = StylePreset
        fields = ['name', 'description', 'instruction_text']
        widgets = {
            'description': forms.TextInput(attrs={'placeholder': 'Short description'}),
            'instruction_text': forms.Textarea(attrs={'rows': 5}),
        }


class RunLabForm(forms.Form):
    name = forms.CharField(max_length=120, required=False)
    prompt_profile = forms.ModelChoiceField(queryset=PromptProfile.objects.all())
    selected_model = forms.ChoiceField(label='Model')
    seed_problem_override = forms.CharField(widget=forms.Textarea(attrs={'rows': 6}), required=False)
    baseline_override = forms.CharField(widget=forms.Textarea(attrs={'rows': 6}), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        model_choices = get_model_choice_options()
        self.fields['selected_model'].choices = model_choices
        self.fields['selected_model'].initial = model_choices[0][0]


class BatchLabForm(forms.ModelForm):
    prompt_profiles = forms.ModelMultipleChoiceField(
        queryset=PromptProfile.objects.all(),
        label='Prompt profiles',
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = BatchGroup
        fields = ['name', 'selected_model', 'seed_problem_override', 'baseline_override', 'repetitions']
        widgets = {
            'seed_problem_override': forms.Textarea(attrs={'rows': 5}),
            'baseline_override': forms.Textarea(attrs={'rows': 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        model_choices = get_model_choice_options()
        self.fields['selected_model'].label = 'Model'
        self.fields['selected_model'].widget = forms.Select(choices=model_choices)
        self.fields['selected_model'].initial = model_choices[0][0]
        if self.instance.pk:
            self.fields['prompt_profiles'].initial = self.instance.prompt_profiles.all()

    def clean_prompt_profiles(self):
        profiles = self.cleaned_data['prompt_profiles']
        if not profiles:
            raise forms.ValidationError('Select at least one prompt profile.')
        return profiles

    def save(self, commit=True):
        profiles = self.cleaned_data['prompt_profiles']
        instance = super().save(commit=False)
        instance.prompt_profile = profiles[0]
        if commit:
            instance.save()
            self.save_m2m()
            instance.prompt_profiles.set(profiles)
        else:
            self._pending_prompt_profiles = profiles
        return instance


class EvaluationReviewForm(forms.ModelForm):
    class Meta:
        model = EvaluationReview
        fields = [
            'reviewer_name',
            'knowledge_alignment',
            'difficulty_appropriateness',
            'structural_completeness',
            'novelty',
            'comment',
        ]


class LearningSessionCreateForm(forms.ModelForm):
    class Meta:
        model = LearningSession
        fields = ['participant_code', 'prompt_profile', 'selected_model', 'seed_problem_text', 'target_turns']
        widgets = {
            'seed_problem_text': forms.Textarea(attrs={'rows': 6}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        model_choices = get_model_choice_options()
        self.fields['selected_model'].label = 'Model'
        self.fields['selected_model'].widget = forms.Select(choices=model_choices)
        self.fields['selected_model'].initial = model_choices[0][0]


class LearningTurnSubmitForm(forms.ModelForm):
    class Meta:
        model = LearningTurn
        fields = ['learner_answer']
        widgets = {
            'learner_answer': forms.Textarea(attrs={'rows': 12, 'placeholder': 'Write your Python solution here.'}),
        }


class QuestionnaireForm(forms.ModelForm):
    class Meta:
        model = Questionnaire
        exclude = ['session', 'created_at']
