FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
 && rm -rf /var/lib/apt/lists/*

COPY Backend/requirements.txt /app/requirements.txt

# Chromium renders the investor memo PDF and captures competitor homepages.
RUN pip install -r /app/requirements.txt \
    && playwright install --with-deps chromium

COPY Backend /app

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

