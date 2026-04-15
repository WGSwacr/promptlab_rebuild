from textwrap import dedent


JSON_SCHEMA = dedent(
    '''
    Return strict JSON only using this structure:
    {
      "title": "title of the problem",
      "baseline": ["relative baseline 1", "relative baseline 2"],
      "difficulty": "easy|medium|hard",
      "description": "content of the problem",
      "sampletests": [
        {
          "sample_input": "sample input shown to the learner",
          "sample_output": "sample output shown to the learner",
          "sample_explanation": "why the sample output is correct"
        }
      ],
      "tests": [
        {"input": "hidden test input", "output": "expected output"}
      ],
      "hints": "partial sample code with blanks left for the learner to fill in"
    }

    Rules:
    - "baseline" can be a single string or an array of strings.
    - "sampletests" are visible examples for the learner and should not duplicate the hidden tests exactly.
    - "tests" are for system evaluation only.
    - "hints" should be code-like guidance with blanks for the key logic. The number of blanks should depend on the generated difficulty.
    '''
).strip()


def _instruction_text(preset):
    return preset.instruction_text.strip() if preset else ''


def _style_text(style_presets):
    texts = []
    for preset in style_presets or []:
        text = getattr(preset, 'instruction_text', '').strip()
        if text:
            texts.append(f'- {preset.name}: {text}')
    return '\n'.join(texts)


def build_assembled_prompt(profile, seed_problem=None, baseline=None, difficulty_preset=None, style_presets=None, extra_context=''):
    seed_problem = (seed_problem or profile.seed_problem_text).strip()
    baseline = (baseline or profile.baseline_text).strip()
    difficulty_text = _instruction_text(difficulty_preset)
    if style_presets is None:
        style_presets = list(profile.style_presets.all())
    style_text = _style_text(style_presets)
    blocks = [
        f'TASK INSTRUCTION:\n{profile.task_instruction.text.strip()}',
        f'CURRICULUM:\n{profile.curriculum_text.strip()}',
        f'SEED PROBLEM:\n{seed_problem}',
        f'BASELINE:\n{baseline}',
    ]
    if difficulty_text:
        blocks.append(f'DIFFICULTY INSTRUCTION:\n{difficulty_text}')
    if style_text:
        blocks.append(f'STYLE INSTRUCTIONS:\n{style_text}')
    if extra_context.strip():
        blocks.append(f'ADDITIONAL SESSION CONTEXT:\n{extra_context.strip()}')
    blocks.append(JSON_SCHEMA)
    return '\n\n'.join(blocks)


def build_run_messages(profile, assembled_prompt):
    return [
        {'role': 'system', 'content': profile.system_prompt.text.strip()},
        {'role': 'user', 'content': assembled_prompt},
    ]


def build_baseline_messages(profile_like):
    user_prompt = dedent(
        f'''
        Based on the following curriculum and seed problem, generate a concise baseline knowledge list.
        Return plain text only. Use short bullet points.

        CURRICULUM:
        {profile_like.curriculum_text.strip()}

        SEED PROBLEM:
        {profile_like.seed_problem_text.strip()}
        '''
    ).strip()
    return [
        {'role': 'system', 'content': profile_like.system_prompt.text.strip()},
        {'role': 'user', 'content': user_prompt},
    ]
