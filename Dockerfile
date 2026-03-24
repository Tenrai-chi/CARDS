FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=True
ENV PYTHONUNBUFFERED=True

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && update-ca-certificates
RUN pip install --upgrade pip
COPY requirements.txt /app/
RUN apt-get update && apt-get install -y libpq-dev build-essential\
    && pip install --no-cache-dir -r requirements.txt --timeout 100\
    && rm -rf /var/lib/apt/lists/*

COPY . /app/

COPY wait /wait
RUN chmod +x /wait

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
