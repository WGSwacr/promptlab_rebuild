import json
import random
from types import SimpleNamespace

from django.contrib import messages
from django.http import QueryDict
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import (
    BatchLabForm,
    DifficultyPresetCreateForm,
    EvaluationReviewForm,
    LearningSessionCreateForm,
    LearningTurnSubmitForm,
    PromptProfileForm,
    QuestionnaireForm,
    RunLabForm,
    StylePresetCreateForm,
    SystemPromptCreateForm,
    TaskInstructionCreateForm,
)
from .models import (
    BatchGroup,
    DifficultyPreset,
    ExperimentRun,
    LearningSession,
    LearningTurn,
    PromptProfile,
    StylePreset,
    SystemPrompt,
    TaskInstruction,
)
from .services.analysis import (
    generated_exercise_quality,
    generated_exercise_quality_matrix,
    learning_support_results,
    questionnaire_results,
    representative_case,
    system_performance,
    system_performance_matrix,
)
from .services.learning import create_first_turn, grade_turn, maybe_advance_session
from .services.llm import LLMError, chat_completion, extract_content
from .services.model_catalog import resolve_model_choice
from .services.prompt_builder import build_assembled_prompt, build_baseline_messages
from .services.runner import execute_batch, execute_run


def home(request):
    return redirect('prompt_settings')


def prompt_settings_list(request):
    profiles = PromptProfile.objects.select_related('system_prompt', 'task_instruction').prefetch_related(
        'difficulty_presets', 'style_presets'
    )
    return render(request, 'lab/prompt_settings_list.html', {'profiles': profiles})


def _selected_single(form, field_name, model_cls):
    if form.is_bound:
        raw_id = form.data.get(field_name)
        if raw_id:
            return model_cls.objects.filter(pk=raw_id).first()
    raw_id = form.initial.get(field_name) if hasattr(form, 'initial') else None
    if raw_id:
        raw_id = getattr(raw_id, 'pk', raw_id)
        return model_cls.objects.filter(pk=raw_id).first()
    if form.instance and getattr(form.instance, 'pk', None):
        return getattr(form.instance, field_name, None)
    return None


def _selected_many(form, field_name, model_cls):
    if form.is_bound:
        ids = form.data.getlist(field_name)
        if ids:
            return list(model_cls.objects.filter(pk__in=ids).order_by('name'))
        return []
    initial_ids = form.initial.get(field_name) if hasattr(form, 'initial') else None
    if initial_ids:
        normalized_ids = [str(getattr(value, 'pk', value)) for value in initial_ids]
        return list(model_cls.objects.filter(pk__in=normalized_ids).order_by('name'))
    if form.instance and getattr(form.instance, 'pk', None):
        return list(getattr(form.instance, field_name).all())
    return []


def _preview_prompt_from_form(form):
    selected_system = _selected_single(form, 'system_prompt', SystemPrompt)
    selected_task = _selected_single(form, 'task_instruction', TaskInstruction)
    difficulty_presets = _selected_many(form, 'difficulty_presets', DifficultyPreset)
    style_presets = _selected_many(form, 'style_presets', StylePreset)
    if form.is_bound:
        curriculum_text = form.data.get('curriculum_text', '')
        seed_problem_text = form.data.get('seed_problem_text', '')
        baseline_text = form.data.get('baseline_text', '')
    else:
        curriculum_text = form.initial.get('curriculum_text', getattr(form.instance, 'curriculum_text', ''))
        seed_problem_text = form.initial.get('seed_problem_text', getattr(form.instance, 'seed_problem_text', ''))
        baseline_text = form.initial.get('baseline_text', getattr(form.instance, 'baseline_text', ''))
    if not (selected_system and selected_task and curriculum_text.strip() and seed_problem_text.strip()):
        return ''
    preview_profile = SimpleNamespace(
        system_prompt=selected_system,
        task_instruction=selected_task,
        curriculum_text=curriculum_text,
        seed_problem_text=seed_problem_text,
        baseline_text=baseline_text,
    )
    difficulty_preview = random.choice(difficulty_presets) if difficulty_presets else None
    return build_assembled_prompt(
        preview_profile,
        difficulty_preset=difficulty_preview,
        style_presets=style_presets,
    )


def _build_profile_snapshot_data(request):
    snapshot_raw = request.POST.get('profile_snapshot', '').strip()
    if not snapshot_raw:
        return QueryDict('', mutable=True)

    try:
        snapshot = json.loads(snapshot_raw)
    except json.JSONDecodeError:
        return QueryDict('', mutable=True)

    data = QueryDict('', mutable=True)
    single_fields = [
        'name',
        'description',
        'system_prompt',
        'task_instruction',
        'curriculum_text',
        'seed_problem_text',
        'baseline_text',
    ]
    list_fields = ['difficulty_presets', 'style_presets']

    for field in single_fields:
        value = snapshot.get(field, '')
        if value is None:
            value = ''
        data[field] = str(value)

    for field in list_fields:
        values = snapshot.get(field, []) or []
        data.setlist(field, [str(value) for value in values])

    return data


def _profile_initial_from_data(data):
    return {
        'name': data.get('name', ''),
        'description': data.get('description', ''),
        'system_prompt': data.get('system_prompt', ''),
        'task_instruction': data.get('task_instruction', ''),
        'curriculum_text': data.get('curriculum_text', ''),
        'seed_problem_text': data.get('seed_problem_text', ''),
        'baseline_text': data.get('baseline_text', ''),
        'difficulty_presets': data.getlist('difficulty_presets'),
        'style_presets': data.getlist('style_presets'),
    }


def _render_profile_form(request, form, profile=None, *, system_form=None, task_form=None, difficulty_form=None, style_form=None):
    system_form = system_form or SystemPromptCreateForm(prefix='system_library')
    task_form = task_form or TaskInstructionCreateForm(prefix='task_library')
    difficulty_form = difficulty_form or DifficultyPresetCreateForm(prefix='difficulty_library')
    style_form = style_form or StylePresetCreateForm(prefix='style_library')
    selected_system = _selected_single(form, 'system_prompt', SystemPrompt)
    selected_task = _selected_single(form, 'task_instruction', TaskInstruction)
    selected_difficulties = _selected_many(form, 'difficulty_presets', DifficultyPreset)
    selected_styles = _selected_many(form, 'style_presets', StylePreset)
    assembled_prompt = _preview_prompt_from_form(form)
    system_prompt_choices = [
        {'id': prompt.pk, 'name': prompt.name, 'text': prompt.text}
        for prompt in SystemPrompt.objects.all()
    ]
    task_instruction_choices = [
        {'id': task.pk, 'name': task.name, 'text': task.text}
        for task in TaskInstruction.objects.all()
    ]
    difficulty_preset_choices = [
        {
            'id': preset.pk,
            'name': preset.name,
            'description': preset.description,
            'instruction_text': preset.instruction_text,
        }
        for preset in DifficultyPreset.objects.all()
    ]
    style_preset_choices = [
        {
            'id': preset.pk,
            'name': preset.name,
            'description': preset.description,
            'instruction_text': preset.instruction_text,
        }
        for preset in StylePreset.objects.all()
    ]
    return render(
        request,
        'lab/prompt_profile_form.html',
        {
            'form': form,
            'profile': profile,
            'assembled_prompt': assembled_prompt,
            'selected_system': selected_system,
            'selected_task': selected_task,
            'selected_difficulties': selected_difficulties,
            'selected_styles': selected_styles,
            'system_form': system_form,
            'task_form': task_form,
            'difficulty_form': difficulty_form,
            'style_form': style_form,
            'system_prompt_choices': system_prompt_choices,
            'task_instruction_choices': task_instruction_choices,
            'difficulty_preset_choices': difficulty_preset_choices,
            'style_preset_choices': style_preset_choices,
        },
    )


def _generate_baseline_into_form(post_data, *, profile=None):
    mutable = post_data.copy()
    system_prompt_id = mutable.get('system_prompt')
    task_instruction_id = mutable.get('task_instruction')
    curriculum_text = mutable.get('curriculum_text', '').strip()
    seed_problem_text = mutable.get('seed_problem_text', '').strip()
    if not (system_prompt_id and task_instruction_id and curriculum_text and seed_problem_text):
        raise ValueError('Please select a system prompt and a task instruction, then fill in Curriculum Text and Seed Problem Text first.')
    system_prompt = SystemPrompt.objects.filter(pk=system_prompt_id).first()
    task_instruction = TaskInstruction.objects.filter(pk=task_instruction_id).first()
    if not (system_prompt and task_instruction):
        raise ValueError('The selected system prompt or task instruction is invalid.')
    profile_like = SimpleNamespace(
        system_prompt=system_prompt,
        task_instruction=task_instruction,
        curriculum_text=curriculum_text,
        seed_problem_text=seed_problem_text,
    )
    payload = chat_completion(build_baseline_messages(profile_like), temperature=0.1)
    mutable['baseline_text'] = extract_content(payload)
    return mutable


def _handle_prompt_profile_page(request, profile=None):
    action = request.POST.get('action', 'save_profile') if request.method == 'POST' else None
    profile_snapshot = _build_profile_snapshot_data(request) if request.method == 'POST' else None
    if action in {'save_profile', 'generate_baseline'}:
        form = PromptProfileForm(request.POST or None, instance=profile)
    elif profile_snapshot is not None:
        form = PromptProfileForm(instance=profile, initial=_profile_initial_from_data(profile_snapshot))
    else:
        form = PromptProfileForm(instance=profile)
    system_form = SystemPromptCreateForm(
        request.POST if action == 'add_system_prompt' else None,
        prefix='system_library',
    )
    task_form = TaskInstructionCreateForm(
        request.POST if action == 'add_task_instruction' else None,
        prefix='task_library',
    )
    difficulty_form = DifficultyPresetCreateForm(
        request.POST if action == 'add_difficulty_preset' else None,
        prefix='difficulty_library',
    )
    style_form = StylePresetCreateForm(
        request.POST if action == 'add_style_preset' else None,
        prefix='style_library',
    )

    if request.method == 'POST':
        if action == 'save_profile':
            if form.is_valid():
                saved_profile = form.save()
                messages.success(request, 'Prompt profile saved.')
                return redirect('prompt_profile_edit', pk=saved_profile.pk)
            messages.error(request, 'Please correct the errors in the profile form.')

        elif action == 'generate_baseline':
            try:
                new_data = _generate_baseline_into_form(request.POST, profile=profile)
                form = PromptProfileForm(new_data, instance=profile)
                messages.success(request, 'Baseline generated and filled into the form. Save the profile to persist it.')
            except (ValueError, LLMError) as exc:
                messages.error(request, f'Baseline generation failed: {exc}')

        elif action == 'add_system_prompt':
            if system_form.is_valid():
                prompt = system_form.save()
                new_data = profile_snapshot.copy()
                new_data['system_prompt'] = str(prompt.pk)
                form = PromptProfileForm(instance=profile, initial=_profile_initial_from_data(new_data))
                system_form = SystemPromptCreateForm(prefix='system_library')
                messages.success(request, 'System prompt added and selected.')
            else:
                messages.error(request, 'Could not add the system prompt. Please check the form.')

        elif action == 'add_task_instruction':
            if task_form.is_valid():
                task = task_form.save()
                new_data = profile_snapshot.copy()
                new_data['task_instruction'] = str(task.pk)
                form = PromptProfileForm(instance=profile, initial=_profile_initial_from_data(new_data))
                task_form = TaskInstructionCreateForm(prefix='task_library')
                messages.success(request, 'Task instruction added and selected.')
            else:
                messages.error(request, 'Could not add the task instruction. Please check the form.')

        elif action == 'add_difficulty_preset':
            if difficulty_form.is_valid():
                preset = difficulty_form.save()
                new_data = profile_snapshot.copy()
                selected_ids = new_data.getlist('difficulty_presets')
                if str(preset.pk) not in selected_ids:
                    new_data.setlist('difficulty_presets', selected_ids + [str(preset.pk)])
                form = PromptProfileForm(instance=profile, initial=_profile_initial_from_data(new_data))
                difficulty_form = DifficultyPresetCreateForm(prefix='difficulty_library')
                messages.success(request, 'Difficulty preset added and selected.')
            else:
                messages.error(request, 'Could not add the difficulty preset. Please check the form.')

        elif action == 'add_style_preset':
            if style_form.is_valid():
                preset = style_form.save()
                new_data = profile_snapshot.copy()
                selected_ids = new_data.getlist('style_presets')
                if str(preset.pk) not in selected_ids:
                    new_data.setlist('style_presets', selected_ids + [str(preset.pk)])
                form = PromptProfileForm(instance=profile, initial=_profile_initial_from_data(new_data))
                style_form = StylePresetCreateForm(prefix='style_library')
                messages.success(request, 'Style preset added and selected.')
            else:
                messages.error(request, 'Could not add the style preset. Please check the form.')

    return _render_profile_form(
        request,
        form,
        profile=profile,
        system_form=system_form,
        task_form=task_form,
        difficulty_form=difficulty_form,
        style_form=style_form,
    )


def prompt_profile_create(request):
    return _handle_prompt_profile_page(request)


def prompt_profile_edit(request, pk):
    profile = get_object_or_404(PromptProfile, pk=pk)
    return _handle_prompt_profile_page(request, profile=profile)


def prompt_profile_copy(request, pk):
    profile = get_object_or_404(PromptProfile, pk=pk)
    new_profile = PromptProfile.objects.create(
        name=f'{profile.name} Copy',
        description=profile.description,
        system_prompt=profile.system_prompt,
        task_instruction=profile.task_instruction,
        curriculum_text=profile.curriculum_text,
        seed_problem_text=profile.seed_problem_text,
        baseline_text=profile.baseline_text,
    )
    new_profile.difficulty_presets.set(profile.difficulty_presets.all())
    new_profile.style_presets.set(profile.style_presets.all())
    messages.success(request, 'Prompt profile copied.')
    return redirect('prompt_profile_edit', pk=new_profile.pk)


def prompt_profile_generate_baseline(request, pk):
    profile = get_object_or_404(PromptProfile, pk=pk)
    try:
        payload = chat_completion(build_baseline_messages(profile), temperature=0.1)
        profile.baseline_text = extract_content(payload)
        profile.save(update_fields=['baseline_text', 'updated_at'])
        messages.success(request, 'Baseline generated successfully.')
    except LLMError as exc:
        messages.error(request, f'Baseline generation failed: {exc}')
    return redirect('prompt_profile_edit', pk=profile.pk)


def run_lab(request):
    if request.method == 'POST':
        form = RunLabForm(request.POST)
        if form.is_valid():
            profile = form.cleaned_data['prompt_profile']
            run = execute_run(
                profile=profile,
                name=form.cleaned_data.get('name') or f'{profile.name} single run',
                run_type=ExperimentRun.RUN_SINGLE,
                model_choice=form.cleaned_data.get('selected_model', ''),
                seed_problem_override=form.cleaned_data.get('seed_problem_override', ''),
                baseline_override=form.cleaned_data.get('baseline_override', ''),
            )
            if run.parse_success:
                messages.success(request, 'Single run completed.')
            else:
                messages.warning(request, 'Single run saved, but parsing failed.')
            return redirect('run_lab')
    else:
        form = RunLabForm()
    runs = ExperimentRun.objects.filter(run_type=ExperimentRun.RUN_SINGLE).select_related('prompt_profile')
    paginator = Paginator(runs, 1)
    page_obj = paginator.get_page(request.GET.get('page'))
    current_run = page_obj.object_list[0] if page_obj.object_list else None
    review_form = EvaluationReviewForm()
    return render(
        request,
        'lab/run_lab.html',
        {
            'form': form,
            'page_obj': page_obj,
            'current_run': current_run,
            'review_form': review_form,
        },
    )


def experiment_review_create(request, run_id):
    run = get_object_or_404(ExperimentRun, pk=run_id)
    if request.method == 'POST':
        form = EvaluationReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.experiment_run = run
            review.save()
            messages.success(request, 'Evaluation review saved.')
        else:
            messages.error(request, 'Could not save the evaluation review.')
    return redirect(reverse('run_lab'))


def batch_lab(request):
    if request.method == 'POST':
        form = BatchLabForm(request.POST)
        if form.is_valid():
            group = form.save(commit=False)
            group.actual_model = resolve_model_choice(form.cleaned_data.get('selected_model', ''))
            group.save()
            execute_batch(group)
            messages.success(request, 'Batch run completed.')
            return redirect(f"{reverse('batch_lab')}?group={group.pk}")
    else:
        form = BatchLabForm()
    groups = BatchGroup.objects.select_related('prompt_profile').all()
    selected_group = None
    group_id = request.GET.get('group')
    if group_id:
        selected_group = get_object_or_404(BatchGroup, pk=group_id)
    elif groups:
        selected_group = groups.first()
    runs = selected_group.runs.all() if selected_group else ExperimentRun.objects.none()
    paginator = Paginator(runs, 1)
    page_obj = paginator.get_page(request.GET.get('page'))
    current_run = page_obj.object_list[0] if page_obj.object_list else None
    review_form = EvaluationReviewForm()
    return render(
        request,
        'lab/batch_lab.html',
        {
            'form': form,
            'groups': groups,
            'selected_group': selected_group,
            'page_obj': page_obj,
            'current_run': current_run,
            'review_form': review_form,
        },
    )


def learning_lab_home(request):
    if request.method == 'POST':
        form = LearningSessionCreateForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.actual_model = resolve_model_choice(form.cleaned_data.get('selected_model', ''))
            session.save()
            create_first_turn(session)
            messages.success(request, 'Learning session created.')
            return redirect('learning_lab_session', pk=session.pk)
    else:
        form = LearningSessionCreateForm()
    sessions = LearningSession.objects.select_related('prompt_profile').all()
    return render(request, 'lab/learning_lab_home.html', {'form': form, 'sessions': sessions})


def learning_lab_session(request, pk):
    session = get_object_or_404(LearningSession, pk=pk)
    current_turn = session.turns.order_by('round_number').filter(result_label=LearningTurn.RESULT_PENDING).first()
    if request.method == 'POST' and current_turn and session.status == LearningSession.STATUS_ACTIVE:
        form = LearningTurnSubmitForm(request.POST, instance=current_turn)
        if form.is_valid():
            graded_turn, next_difficulty = grade_turn(current_turn, form.cleaned_data['learner_answer'])
            maybe_advance_session(session, graded_turn, next_difficulty)
            if session.status == LearningSession.STATUS_COMPLETED:
                messages.success(request, 'Learning session completed. Please fill in the questionnaire.')
                return redirect('learning_lab_session', pk=session.pk)
            messages.success(request, 'Answer submitted. The next turn has been generated.')
            return redirect('learning_lab_session', pk=session.pk)
    else:
        form = LearningTurnSubmitForm(instance=current_turn)
    turns = session.turns.prefetch_related('grades').all()
    return render(
        request,
        'lab/learning_lab_session.html',
        {
            'session': session,
            'current_turn': current_turn,
            'form': form,
            'turns': turns,
        },
    )


def learning_lab_questionnaire(request, pk):
    session = get_object_or_404(LearningSession, pk=pk)
    if hasattr(session, 'questionnaire'):
        messages.info(request, 'This session already has a questionnaire.')
        return redirect('learning_lab_session', pk=session.pk)
    if request.method == 'POST':
        form = QuestionnaireForm(request.POST)
        if form.is_valid():
            questionnaire = form.save(commit=False)
            questionnaire.session = session
            questionnaire.save()
            messages.success(request, 'Questionnaire submitted.')
            return redirect('analysis')
    else:
        form = QuestionnaireForm()
    return render(request, 'lab/learning_lab_questionnaire.html', {'session': session, 'form': form})


def analysis_page(request):
    context = {
        'system_stats': system_performance(),
        'system_matrix': system_performance_matrix(),
        'quality_stats': generated_exercise_quality(),
        'quality_matrix': generated_exercise_quality_matrix(),
        'learning_stats': learning_support_results(),
        'questionnaire_rows': questionnaire_results(),
        'case_session': representative_case(),
    }
    return render(request, 'lab/analysis.html', context)
