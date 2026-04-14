from django.core.management.base import BaseCommand

from lab.models import DifficultyPreset, StylePreset, SystemPrompt, TaskInstruction


DEFAULT_SYSTEM = 'You are a rigorous programming education assistant. Produce structured, concise, and pedagogically useful exercises.'
DEFAULT_TASK = 'Generate one programming exercise derived from the supplied curriculum, seed problem, and baseline. Keep the topic aligned, vary the problem statement, and include tests for automatic checking.'

DEFAULT_DIFFICULTIES = [
    (
        'Easy',
        'Prefer prerequisite knowledge and straightforward logic.',
        'Generate an easier follow-up question. Keep the topic aligned with the seed problem, reduce cognitive load, and avoid introducing new advanced concepts.',
    ),
    (
        'Medium',
        'Stay close to the original topic and level.',
        'Generate a question at a similar level to the seed problem. Maintain topic continuity and moderate complexity.',
    ),
    (
        'Hard',
        'Increase reasoning depth or combine adjacent knowledge points.',
        'Generate a harder follow-up question. Increase reasoning depth, add constraints, or combine adjacent knowledge points while staying pedagogically coherent.',
    ),
]

DEFAULT_STYLES = [
    (
        'Clear Educational Style',
        'Readable and instruction-focused wording.',
        'Use clear instructional language, concise wording, and explicit problem requirements. Avoid unnecessary verbosity.',
    ),
    (
        'Realistic Scenario Style',
        'Frame the question with a light real-world context.',
        'Add a light real-world scenario to the question so it feels practical, but keep the problem concise and easy to parse.',
    ),
]


class Command(BaseCommand):
    help = 'Create default prompt-library rows.'

    def handle(self, *args, **options):
        system_prompt, _ = SystemPrompt.objects.get_or_create(name='Default System Prompt', defaults={'text': DEFAULT_SYSTEM})
        task_instruction, _ = TaskInstruction.objects.get_or_create(
            name='Default Task Instruction', defaults={'text': DEFAULT_TASK}
        )
        for name, description, instruction_text in DEFAULT_DIFFICULTIES:
            DifficultyPreset.objects.get_or_create(
                name=name,
                defaults={'description': description, 'instruction_text': instruction_text},
            )
        for name, description, instruction_text in DEFAULT_STYLES:
            StylePreset.objects.get_or_create(
                name=name,
                defaults={'description': description, 'instruction_text': instruction_text},
            )
        self.stdout.write(self.style.SUCCESS(f'Seeded: {system_prompt.name} / {task_instruction.name} / preset library'))
