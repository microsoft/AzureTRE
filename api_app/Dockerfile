FROM python:3.12-slim-bookworm AS base

COPY requirements.txt /.
RUN pip3 install --no-cache-dir -r requirements.txt

FROM base AS test
COPY requirements-dev.txt /.
RUN pip3 install --no-cache-dir -r requirements-dev.txt
COPY . /api
WORKDIR /api
RUN ./run_tests_and_exit_succesfully.sh


FROM scratch AS test-results
COPY --from=test /test-results/* /.


FROM base AS runtime
COPY . /api
WORKDIR /api
RUN groupadd -r api && useradd -r -s /bin/false -g api api_user
USER api_user
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:8000", "-k", "uvicorn.workers.UvicornWorker","--timeout", "60", "--workers", "5"]
