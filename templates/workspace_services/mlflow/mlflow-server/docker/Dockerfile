FROM python:3.8-buster

# Install MLflow Python Packages
RUN pip install --no-cache-dir psycopg2==2.9.3 mlflow==1.24.0 azure-storage-blob==12.10.0

RUN apt-get update \
  && apt-get install openssh-server -y --no-install-recommends \
  && apt-get clean -y && rm -rf /var/lib/apt/lists/*

# define default server env variables
ENV MLFLOW_SERVER_HOST 0.0.0.0
ENV MLFLOW_SERVER_PORT 5000
ENV MLFLOW_SERVER_WORKERS 1

COPY ./docker/sshd_config /etc/ssh/
COPY ./docker/startup.sh /usr/local/bin/

EXPOSE 5000 2222
ENTRYPOINT ["sh", "/usr/local/bin/startup.sh"]
