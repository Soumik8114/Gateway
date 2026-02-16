FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY data_plane/ /app/data_plane/

ENV DATABASE_URL=sqlite:////data/db.sqlite3
ENV REDIS_URL=redis://redis:6379

CMD ["uvicorn", "data_plane.fastapi_app.main:app", "--host", "0.0.0.0", "--port", "7000"]

EXPOSE 7000