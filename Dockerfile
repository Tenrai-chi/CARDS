FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=True
ENV PYTHONUNBUFFERED=True

RUN mkdir /app
WORKDIR /app

RUN pip install --upgrade pip
COPY requirements.txt /app/
RUN apt-get update && apt-get install -y libpq-dev build-essential
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

COPY --from=ghcr.io/ufoscout/docker-compose-wait:latest /wait /wait
RUN chmod +x /wait
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
