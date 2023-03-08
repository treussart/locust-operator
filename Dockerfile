ARG PYTHON_VERSION=3.10.3-slim

FROM python:${PYTHON_VERSION} AS base
RUN useradd -d /devops --system -m -s /bin/bash -U devops && \
    pip install pipenv
WORKDIR /devops
COPY --chown=devops:devops ./Pipfile* /devops/

FROM base AS builder
USER devops:devops
RUN pipenv install --deploy

FROM base
USER devops:devops
COPY --from=builder --chown=devops:devops /devops /devops
COPY --chown=devops:devops . /devops
ENV PIPENV_QUIET=1
# turn off python output buffering
ENV PYTHONUNBUFFERED=1
RUN touch .env
ENV PYTHONPATH=$PYTHONPATH:$(pwd)/src
ENTRYPOINT ["pipenv", "run", "operator"]
