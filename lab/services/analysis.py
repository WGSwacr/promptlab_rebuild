from statistics import mean, pstdev

from django.db.models import Avg, Count, Q

from lab.models import BatchGroup, EvaluationReview, ExperimentRun, LearningSession, LearningTurn, Questionnaire


class SummaryStat:
    def __init__(self, label, value):
        self.label = label
        self.value = value


def system_performance():
    total_runs = ExperimentRun.objects.count()
    valid_outputs = ExperimentRun.objects.filter(parse_success=True).count()
    batch_total = BatchGroup.objects.count()
    batch_completed = BatchGroup.objects.filter(status=BatchGroup.STATUS_COMPLETED).count()
    avg_response_ms = ExperimentRun.objects.exclude(response_time_ms__isnull=True).aggregate(avg=Avg('response_time_ms'))['avg'] or 0
    return [
        SummaryStat('Total runs', total_runs),
        SummaryStat('Valid structured outputs', valid_outputs),
        SummaryStat('Structured output rate', f'{(valid_outputs / total_runs * 100):.1f}%' if total_runs else '0.0%'),
        SummaryStat('Batch completion rate', f'{(batch_completed / batch_total * 100):.1f}%' if batch_total else '0.0%'),
        SummaryStat('Average response time', f'{avg_response_ms / 1000:.2f} s' if avg_response_ms else '0.00 s'),
    ]


def generated_exercise_quality():
    agg = EvaluationReview.objects.aggregate(
        knowledge_alignment=Avg('knowledge_alignment'),
        difficulty_appropriateness=Avg('difficulty_appropriateness'),
        structural_completeness=Avg('structural_completeness'),
        novelty=Avg('novelty'),
    )
    values = [value for value in agg.values() if value is not None]
    agg['overall_mean'] = sum(values) / len(values) if values else None
    return agg


def learning_support_results():
    total_sessions = LearningSession.objects.count()
    completed_sessions = LearningSession.objects.filter(status=LearningSession.STATUS_COMPLETED).count()
    avg_rounds = LearningTurn.objects.values('learning_session').annotate(c=Count('id')).aggregate(avg=Avg('c'))['avg'] or 0
    improved_sessions = 0
    for session in LearningSession.objects.filter(status=LearningSession.STATUS_COMPLETED):
        turns = list(session.turns.order_by('round_number'))
        if len(turns) < 2:
            continue
        midpoint = len(turns) // 2
        first = turns[:midpoint]
        second = turns[midpoint:]
        first_acc = mean(turn.accuracy_ratio for turn in first) if first else 0
        second_acc = mean(turn.accuracy_ratio for turn in second) if second else 0
        if second_acc > first_acc:
            improved_sessions += 1
    targeted_total = LearningTurn.objects.exclude(result_label=LearningTurn.RESULT_PENDING).count()
    targeted_success = LearningTurn.objects.filter(
        Q(system_action=LearningTurn.ACTION_EASY) |
        Q(system_action=LearningTurn.ACTION_MEDIUM) |
        Q(system_action=LearningTurn.ACTION_HARD)
    ).exclude(result_label=LearningTurn.RESULT_PENDING).count()
    return [
        SummaryStat('Total learning sessions', total_sessions),
        SummaryStat('Completed sessions', completed_sessions),
        SummaryStat('Session completion rate', f'{(completed_sessions / total_sessions * 100):.1f}%' if total_sessions else '0.0%'),
        SummaryStat('Average rounds per session', f'{avg_rounds:.2f}'),
        SummaryStat('Sessions with improved later-round accuracy', improved_sessions),
        SummaryStat('Targeted follow-up success rate', f'{(targeted_success / targeted_total * 100):.1f}%' if targeted_total else '0.0%'),
    ]


def questionnaire_results():
    items = [
        ('q1_topic_relevance', 'Q1 Topic relevance'),
        ('q2_difficulty_appropriateness', 'Q2 Difficulty appropriateness'),
        ('q3_clarity', 'Q3 Clarity of problem statement'),
        ('q4_adaptive_followup', 'Q4 Adaptive follow-up relevance'),
        ('q5_step_by_step_support', 'Q5 Step-by-step support'),
        ('q6_weak_point_identification', 'Q6 Weak-point identification'),
        ('q7_ease_of_interaction', 'Q7 Ease of interaction'),
        ('q8_readability', 'Q8 Readability of output'),
        ('q9_willingness_to_reuse', 'Q9 Willingness to reuse'),
        ('q10_overall_helpfulness', 'Q10 Overall helpfulness'),
    ]
    all_responses = list(Questionnaire.objects.all())
    rows = []
    for field, label in items:
        values = [getattr(item, field) for item in all_responses]
        rows.append({
            'label': label,
            'mean': round(mean(values), 2) if values else None,
            'sd': round(pstdev(values), 2) if len(values) > 1 else (0 if values else None),
        })
    return rows


def representative_case():
    return LearningSession.objects.filter(status=LearningSession.STATUS_COMPLETED).order_by('-completed_at', '-created_at').first()
