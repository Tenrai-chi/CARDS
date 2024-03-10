FROM python:3.9-bookworm

RUN mkdir app
WORKDIR app

ADD . /app/

RUN pip install -r requirements.txt

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]