

celery -A app.tasks.celery_app worker --loglevel=info

uvicorn app.main:app --reload --host 0.0.0.0 --port 31234

npm run dev