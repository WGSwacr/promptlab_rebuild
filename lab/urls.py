from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('prompt-settings/', views.prompt_settings_list, name='prompt_settings'),
    path('prompt-settings/new/', views.prompt_profile_create, name='prompt_profile_create'),
    path('prompt-settings/<int:pk>/', views.prompt_profile_edit, name='prompt_profile_edit'),
    path('prompt-settings/<int:pk>/copy/', views.prompt_profile_copy, name='prompt_profile_copy'),
    path('prompt-settings/<int:pk>/baseline/', views.prompt_profile_generate_baseline, name='prompt_profile_generate_baseline'),
    path('run-lab/', views.run_lab, name='run_lab'),
    path('run-lab/<int:run_id>/review/', views.experiment_review_create, name='experiment_review_create'),
    path('batch-lab/', views.batch_lab, name='batch_lab'),
    path('learning-lab/', views.learning_lab_home, name='learning_lab'),
    path('learning-lab/session/<int:pk>/', views.learning_lab_session, name='learning_lab_session'),
    path('learning-lab/session/<int:pk>/questionnaire/', views.learning_lab_questionnaire, name='learning_lab_questionnaire'),
    path('analysis/', views.analysis_page, name='analysis'),
]
