import random
import time

from django.utils import timezone

from lab.models import BatchGroup, ExperimentRun
from .model_catalog import resolve_model_choice
from .llm import chat_completion, extract_content
from .parser import parse_json_from_text
from .prompt_builder import build_assembled_prompt, build_run_messages


def _choose_difficulty(profile, difficulty_hint=''):
    presets = list(profile.difficulty_presets.all())
    if not presets:
        return None
    if difficulty_hint:
        hint = difficulty_hint.strip().lower()
        matched = [preset for preset in presets if hint in preset.name.lower()]
        if matched:
            return random.choice(matched)
    return random.choice(presets)


def _choose_styles(profile):
    return list(profile.style_presets.all())


def execute_run(
    *,
    profile,
    name,
    run_type,
    seed_problem_override='',
    baseline_override='',
    batch_group=None,
    extra_context='',
    difficulty_hint='',
    model_choice='',
):
    effective_seed = seed_problem_override.strip() or profile.seed_problem_text
    effective_baseline = baseline_override.strip() or profile.baseline_text
    difficulty = _choose_difficulty(profile, difficulty_hint=difficulty_hint)
    styles = _choose_styles(profile)
    actual_model = resolve_model_choice(model_choice)
    assembled_prompt = build_assembled_prompt(
        profile,
        seed_problem=effective_seed,
        baseline=effective_baseline,
        difficulty_preset=difficulty,
        style_presets=styles,
        extra_context=extra_context,
    )
    run = ExperimentRun.objects.create(
        name=name or f'{profile.name} run',
        prompt_profile=profile,
        run_type=run_type,
        batch_group=batch_group,
        seed_problem_override=seed_problem_override,
        baseline_override=baseline_override,
        requested_model=model_choice,
        actual_model=actual_model,
        effective_seed_problem=effective_seed,
        effective_baseline=effective_baseline,
        effective_difficulty=difficulty.name if difficulty else '',
        effective_style=', '.join(style.name for style in styles),
        assembled_prompt=assembled_prompt,
    )
    started = time.perf_counter()
    try:
        payload = chat_completion(build_run_messages(profile, assembled_prompt), model=actual_model)
        raw_response = extract_content(payload)
        parsed = parse_json_from_text(raw_response)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        run.raw_response = raw_response
        run.structured_output = parsed
        run.parse_success = True
        run.response_time_ms = elapsed_ms
        run.save(update_fields=['raw_response', 'structured_output', 'parse_success', 'response_time_ms'])
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        run.error_message = str(exc)
        run.response_time_ms = elapsed_ms
        run.save(update_fields=['error_message', 'response_time_ms'])
    return run


def execute_batch(group):
    group.status = BatchGroup.STATUS_RUNNING
    group.save(update_fields=['status'])
    try:
        profiles = list(group.prompt_profiles.all()) or [group.prompt_profile]
        for idx in range(1, group.repetitions + 1):
            for profile in profiles:
                execute_run(
                    profile=profile,
                    name=f'{group.name} / {profile.name} #{idx}',
                    run_type=ExperimentRun.RUN_BATCH,
                    seed_problem_override=group.seed_problem_override,
                    baseline_override=group.baseline_override,
                    batch_group=group,
                    model_choice=group.actual_model or group.selected_model,
                )
        group.status = BatchGroup.STATUS_COMPLETED
    except Exception:
        group.status = BatchGroup.STATUS_FAILED
        raise
    finally:
        group.completed_at = timezone.now()
        group.save(update_fields=['status', 'completed_at'])
    return group
