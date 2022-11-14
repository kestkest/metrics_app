FROM python:3.9
ENV TZ=Europe/Moscow \
    LANG=C.UTF-8 \
    PYTHONPATH=/code \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on

EXPOSE 8080

COPY pyproject.toml poetry.lock ./
RUN pip3 install poetry
RUN poetry config virtualenvs.create false
RUN poetry install --no-dev --no-interaction --no-ansi

RUN mkdir /code
WORKDIR /code

ADD . /code/
ENTRYPOINT ["python", "app/main.py"]