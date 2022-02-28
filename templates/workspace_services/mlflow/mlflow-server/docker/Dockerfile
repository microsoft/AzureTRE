FROM python:3.8-buster

# Install MLflow Python Packages
RUN pip install mlflow
# RUN pip install mlflow[extras]
# RUN pip install mlflow-skinny sqlalchemy alembic sqlparse
# RUN pip install scikit-learn

RUN apt-get update && apt-get install openssh-server -y --no-install-recommends

# define default server env variables
ENV MLFLOW_SERVER_HOST 0.0.0.0
ENV MLFLOW_SERVER_PORT 5000
ENV MLFLOW_SERVER_WORKERS 1

COPY sshd_config /etc/ssh/
COPY startup.sh /usr/local/bin/

RUN ["chmod", "u+x", "/usr/local/bin/startup.sh"]

EXPOSE 5000 2222
ENTRYPOINT ["sh", "./startup.sh"]
