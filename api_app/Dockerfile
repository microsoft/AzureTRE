FROM python:3.8-slim-bullseye as base
COPY requirements.txt /.
RUN pip3 install --no-cache-dir -r requirements.txt

FROM base as test
COPY requirements-dev.txt /.
RUN pip3 install --no-cache-dir -r requirements-dev.txt
COPY . /api
WORKDIR /api
RUN ./run_tests_and_exit_succesfully.sh


FROM scratch as test-results
COPY --from=test /test-results/* /.


FROM base as runtime
COPY . /api
WORKDIR /api
RUN groupadd -r api && useradd -r -s /bin/false -g api api_user
USER api_user
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port 8000"]
