FROM python:3.11 AS base
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV PYTHONPATH=.
RUN mkdir /app
WORKDIR /app

RUN python3 -m venv $VIRTUAL_ENV

RUN apt-get update && \
    apt-get install -y \
	--no-install-recommends \
	make python3-dev 

RUN pip install poetry 
COPY README.md pyproject.toml poetry.lock ./
RUN poetry run pip install setuptools wheel packaging
RUN poetry install --no-root --compile --no-dev

COPY auto_dev auto_dev
RUN poetry install --compile --no-dev

ENV PATH="$VIRTUAL_ENV/bin:$PATH"


RUN echo $VIRTUAL_ENV
RUN poetry env info
ENTRYPOINT ["poetry", "run"]
ENV PYTHONUNBUFFERED=TRUE

CMD ["--help"]

