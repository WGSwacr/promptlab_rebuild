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


def system_performance_by_profile():
    rows = []
    batch_totals = {
        item['prompt_profiles__name']: item
        for item in BatchGroup.objects.values('prompt_profiles__name').annotate(
            total_groups=Count('id', distinct=True),
            completed_groups=Count('id', filter=Q(status=BatchGroup.STATUS_COMPLETED), distinct=True),
        )
        if item['prompt_profiles__name']
    }
    for item in ExperimentRun.objects.values('prompt_profile__name').annotate(
        total_runs=Count('id'),
        valid_outputs=Count('id', filter=Q(parse_success=True)),
        avg_response_ms=Avg('response_time_ms'),
    ).order_by('prompt_profile__name'):
        total_runs = item['total_runs'] or 0
        valid_outputs = item['valid_outputs'] or 0
        avg_response_ms = item['avg_response_ms'] or 0
        profile_name = item['prompt_profile__name'] or '-'
        batch_info = batch_totals.get(profile_name, {})
        batch_total = batch_info.get('total_groups', 0) or 0
        batch_completed = batch_info.get('completed_groups', 0) or 0
        rows.append({
            'profile': profile_name,
            'total_runs': total_runs,
            'valid_outputs': valid_outputs,
            'structured_output_rate': f'{(valid_outputs / total_runs * 100):.1f}%' if total_runs else '0.0%',
            'batch_completion_rate': f'{(batch_completed / batch_total * 100):.1f}%' if batch_total else '0.0%',
            'avg_response_time': f'{avg_response_ms / 1000:.2f} s' if avg_response_ms else '0.00 s',
        })
    return rows


def system_performance_matrix():
    overall_rows = system_performance()
    overall_map = {item.label: item.value for item in overall_rows}
    profile_rows = system_performance_by_profile()
    columns = ['Overall'] + [row['profile'] for row in profile_rows]
    metrics = [
        ('Total runs', 'total_runs'),
        ('Valid structured outputs', 'valid_outputs'),
        ('Structured output rate', 'structured_output_rate'),
        ('Batch completion rate', 'batch_completion_rate'),
        ('Average response time', 'avg_response_time'),
    ]
    overall_key_map = {
        'Total runs': 'Total runs',
        'Valid structured outputs': 'Valid structured outputs',
        'Structured output rate': 'Structured output rate',
        'Batch completion rate': 'Batch completion rate',
        'Average response time': 'Average response time',
    }
    rows = []
    for label, key in metrics:
        values = [overall_map.get(overall_key_map[label], '-')]
        values.extend(row.get(key, '-') for row in profile_rows)
        rows.append({'label': label, 'values': values})
    return {'columns': columns, 'rows': rows}


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


def generated_exercise_quality_by_profile():
    rows = []
    for item in EvaluationReview.objects.values('experiment_run__prompt_profile__name').annotate(
        knowledge_alignment=Avg('knowledge_alignment'),
        difficulty_appropriateness=Avg('difficulty_appropriateness'),
        structural_completeness=Avg('structural_completeness'),
        novelty=Avg('novelty'),
        review_count=Count('id'),
    ).order_by('experiment_run__prompt_profile__name'):
        values = [
            item['knowledge_alignment'],
            item['difficulty_appropriateness'],
            item['structural_completeness'],
            item['novelty'],
        ]
        filtered = [value for value in values if value is not None]
        rows.append({
            'profile': item['experiment_run__prompt_profile__name'] or '-',
            'review_count': item['review_count'],
            'knowledge_alignment': round(item['knowledge_alignment'], 2) if item['knowledge_alignment'] is not None else None,
            'difficulty_appropriateness': round(item['difficulty_appropriateness'], 2) if item['difficulty_appropriateness'] is not None else None,
            'structural_completeness': round(item['structural_completeness'], 2) if item['structural_completeness'] is not None else None,
            'novelty': round(item['novelty'], 2) if item['novelty'] is not None else None,
            'overall_mean': round(sum(filtered) / len(filtered), 2) if filtered else None,
        })
    return rows


def generated_exercise_quality_matrix():
    overall = generated_exercise_quality()
    profile_rows = generated_exercise_quality_by_profile()
    columns = ['Overall'] + [row['profile'] for row in profile_rows]
    metrics = [
        ('Knowledge alignment', 'knowledge_alignment'),
        ('Difficulty appropriateness', 'difficulty_appropriateness'),
        ('Structural completeness', 'structural_completeness'),
        ('Novelty', 'novelty'),
        ('Overall mean', 'overall_mean'),
    ]
    rows = []
    for label, key in metrics:
        overall_value = overall.get(key)
        values = [round(overall_value, 2) if overall_value is not None else '-']
        values.extend(
            row.get(key) if row.get(key) is not None else '-'
            for row in profile_rows
        )
        rows.append({'label': label, 'values': values})
    return {'columns': columns, 'rows': rows}


def learning_support_results():
    total_sessions = LearningSession.objects.count()
    completed_sessions = LearningSession.objects.filter(status=LearningSession.STATUS_COMPLETED).count()
    avg_rounds = LearningTurn.objects.values('learning_session').annotate(c=Count('id')).aggregate(avg=Avg('c'))['avg'] or 0
    answered_turns = LearningTurn.objects.exclude(result_label=LearningTurn.RESULT_PENDING)
    total_answered_turns = answered_turns.count()
    avg_turn_accuracy = answered_turns.aggregate(avg=Avg('accuracy_ratio'))['avg'] or 0
    fully_correct_turns = answered_turns.filter(result_label=LearningTurn.RESULT_CORRECT).count()
    questionnaire_completed = Questionnaire.objects.count()
    return [
        SummaryStat('Total learning sessions', total_sessions),
        SummaryStat('Completed sessions', completed_sessions),
        SummaryStat('Session completion rate', f'{(completed_sessions / total_sessions * 100):.1f}%' if total_sessions else '0.0%'),
        SummaryStat('Average rounds per session', f'{avg_rounds:.2f}'),
        SummaryStat('Total answered turns', total_answered_turns),
        SummaryStat('Average turn accuracy', f'{avg_turn_accuracy * 100:.1f}%'),
        SummaryStat('Fully correct turn rate', f'{(fully_correct_turns / total_answered_turns * 100):.1f}%' if total_answered_turns else '0.0%'),
        SummaryStat('Questionnaire completion rate', f'{(questionnaire_completed / completed_sessions * 100):.1f}%' if completed_sessions else '0.0%'),
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
