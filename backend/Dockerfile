FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && if [ \"$ENVIRONMENT\" != \"production\" ]; then python -c 'from database import SessionLocal; from seed_data import seed_demo_profiles; db=SessionLocal(); seed_demo_profiles(db); db.close()'; fi && uvicorn main:app --host 0.0.0.0 --port 8000"]