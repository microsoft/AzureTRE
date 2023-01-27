# To enable ssh & remote debugging on app service change the base image to the one below
# FROM mcr.microsoft.com/azure-functions/python:3.0-python3.8-appservice
FROM --platform=linux/amd64 mcr.microsoft.com/azure-functions/python:3.0-python3.8 as base
COPY requirements.txt /
RUN pip install --no-cache-dir -r /requirements.txt


FROM base as test
COPY requirements-dev.txt /
RUN pip install --no-cache-dir -r /requirements-dev.txt
WORKDIR /app
COPY . .
RUN /app/run_tests_and_exit_succesfully.sh


FROM scratch as test-results
COPY --from=test /test-results/* /


FROM base as runtime
ENV AzureWebJobsScriptRoot=/home/site/wwwroot \
    AzureFunctionsJobHost__Logging__Console__IsEnabled=true
COPY . /home/site/wwwroot
