# PromptLab Rebuild

A clean Django-only rebuild of the original `llm-prompt-lab` project.

## Highlights

- Pure Django server-rendered pages
- No JavaScript dependency for core workflows
- Prompt Settings, Run Lab, Batch Lab, Learning Lab, Analysis
- Baseline generation via LM Studio/OpenAI-compatible API
- Questionnaire-based case study support
- Analysis page aligned to thesis Chapter 4 tables

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_defaults
python manage.py runserver
```

## Environment variables

```bash
export DJANGO_SECRET_KEY='change-me'
export DJANGO_DEBUG='1'
export DJANGO_ALLOWED_HOSTS='127.0.0.1,localhost'
export LM_STUDIO_BASE_URL='http://127.0.0.1:1234'
export LM_STUDIO_API_KEY='lm-studio'
export LM_STUDIO_MODEL='openai/gpt-oss-20b'
export LM_STUDIO_TEMPERATURE='0.2'
export LM_STUDIO_CHAT_TIMEOUT='60'
```

## Suggested workflow

1. Run `seed_defaults` to create a starter System Prompt and Task Instruction.
2. Open `/prompt-settings/` and create a prompt profile.
3. Use the "Generate baseline" action once the profile content is ready.
4. Test profiles in Run Lab or Batch Lab.
5. Collect manual review scores and learning sessions.
6. Use Analysis as the direct source for Chapter 4 tables.
