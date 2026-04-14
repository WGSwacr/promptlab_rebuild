from django.utils import timezone

from lab.models import LearningSession, LearningTurn, TurnGrade
from .code_runner import execute_python_code
from .runner import execute_run


def _result_from_accuracy(correct_count, total_count):
    if total_count <= 0:
        return LearningTurn.RESULT_INCORRECT, 'easy', LearningTurn.ACTION_EASY
    ratio = correct_count / total_count
    if ratio == 1:
        return LearningTurn.RESULT_CORRECT, 'hard', LearningTurn.ACTION_HARD
    if ratio == 0:
        return LearningTurn.RESULT_INCORRECT, 'easy', LearningTurn.ACTION_EASY
    return LearningTurn.RESULT_PARTIAL, 'medium', LearningTurn.ACTION_MEDIUM


def _learning_context(session):
    lines = []
    for turn in session.turns.order_by('round_number'):
        if turn.result_label == LearningTurn.RESULT_PENDING:
            continue
        lines.append(
            f'Round {turn.round_number}: focus={turn.generated_focus}; result={turn.result_label}; next={turn.system_action}'
        )
    return '\n'.join(lines[-2:])


def create_first_turn(session):
    return create_next_turn(session=session, difficulty_hint='medium')


def create_next_turn(session, difficulty_hint):
    extra_context = _learning_context(session)
    run = execute_run(
        profile=session.prompt_profile,
        name=f'{session.participant_code} round {session.completed_turns + 1}',
        run_type='single',
        difficulty_hint=difficulty_hint,
        model_choice=session.actual_model or session.selected_model,
        extra_context=(
            'Generate exactly one follow-up question for a learning session. '
            f'Target difficulty: {difficulty_hint}.\n{extra_context}'
        ),
    )
    payload = run.structured_output if run.parse_success else {}
    next_round = session.completed_turns + 1
    turn = LearningTurn.objects.create(
        learning_session=session,
        round_number=next_round,
        generated_focus=str(payload.get('focus', '')),
        generated_question=str(payload.get('question', run.raw_response or run.error_message or 'Generation failed.')),
        model_used=run.actual_model,
        difficulty_used=str(payload.get('difficulty', difficulty_hint)),
        question_payload=payload,
    )
    tests = payload.get('tests') or []
    for index, item in enumerate(tests, start=1):
        TurnGrade.objects.create(
            learning_turn=turn,
            case_order=index,
            test_input=str(item.get('input', '')),
            expected_output=str(item.get('output', '')),
        )
    return turn


def grade_turn(turn, learner_answer):
    turn.learner_answer = learner_answer
    grades = list(turn.grades.all())
    correct_count = 0
    for grade in grades:
        try:
            result = execute_python_code(learner_answer, grade.test_input)
            grade.learner_output = result.stdout
            if result.returncode != 0:
                grade.error_message = result.stderr
                grade.is_correct = False
            else:
                grade.is_correct = result.stdout.strip() == grade.expected_output.strip()
                if grade.is_correct:
                    correct_count += 1
        except Exception as exc:
            grade.error_message = str(exc)
            grade.is_correct = False
        grade.save(update_fields=['learner_output', 'error_message', 'is_correct'])
    total_count = len(grades)
    result_label, next_difficulty, action = _result_from_accuracy(correct_count, total_count)
    turn.correct_count = correct_count
    turn.total_count = total_count
    turn.accuracy_ratio = (correct_count / total_count) if total_count else 0.0
    turn.result_label = result_label
    turn.system_action = action
    turn.save(
        update_fields=['learner_answer', 'correct_count', 'total_count', 'accuracy_ratio', 'result_label', 'system_action']
    )
    return turn, next_difficulty


def maybe_advance_session(session, turn, next_difficulty):
    if turn.round_number >= session.target_turns:
        session.status = LearningSession.STATUS_COMPLETED
        session.completed_at = timezone.now()
        session.save(update_fields=['status', 'completed_at'])
        return session
    create_next_turn(session=session, difficulty_hint=next_difficulty)
    return session
