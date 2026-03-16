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

EXPOSE 8000

CMD ["python", "omg/manage.py", "runserver", "0.0.0.0:8000"]
