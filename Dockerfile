FROM apache/airflow:2.10.5-python3.11

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow
WORKDIR /opt/airflow/app

COPY --chown=airflow:root pyproject.toml README.md ./
COPY --chown=airflow:root src ./src
COPY --chown=airflow:root config.yaml ./config.yaml
COPY --chown=airflow:root orchestration ./orchestration

RUN pip install --no-cache-dir -e .

ENV PYTHONPATH=/opt/airflow/app/src
