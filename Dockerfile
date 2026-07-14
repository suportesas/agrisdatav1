# Dockerfile para Agrisdata (Django)
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app/agrisdata

# pycairo e freetype-py compilam extensões nativas na instalação
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libcairo2-dev \
    libfreetype6-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# Pastas usadas por STATIC_ROOT, MEDIA_ROOT e logs (ver core/settings.py)
RUN mkdir -p /app/agrisdata/staticfiles /app/agrisdata/media /app/agrisdata/logs

RUN chmod +x scripts/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["scripts/entrypoint.sh"]
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000"]
