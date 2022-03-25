FROM python:3.8-buster

# Install MLflow Python Packages
RUN pip install psycopg2==2.9.3
RUN pip install mlflow==1.24.0
RUN pip install azure-storage-blob==12.10.0

RUN apt-get update && apt-get install openssh-server -y --no-install-recommends

# define default server env variables
ENV MLFLOW_SERVER_HOST 0.0.0.0
ENV MLFLOW_SERVER_PORT 5000
ENV MLFLOW_SERVER_WORKERS 1

COPY ./docker/sshd_config /etc/ssh/
COPY ./docker/startup.sh /usr/local/bin/

EXPOSE 5000 2222
ENTRYPOINT ["sh", "/usr/local/bin/startup.sh"]
