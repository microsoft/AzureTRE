FROM python:3.8

COPY requirements.txt .
RUN pip3 install -r requirements.txt

COPY . /api

WORKDIR /api

RUN groupadd -r api && useradd -r -s /bin/false -g api api_user

USER api_user

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port 8000"]