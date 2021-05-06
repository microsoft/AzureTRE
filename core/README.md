# Core Applications

## TRE API

### Run locally

Install the requirements on the dev machine

```cmd
virtualenv venv
source venv/bin/activate    # linux
venv/Scripts/activate       # windows
pip install -r core/api/requirements.txt
```

Run the webserver locally - from a terminal in the core directory

```cmd
uvicorn api.main:app
```

This will start the API on [http://127.0.0.1:8000](http://127.0.0.1:8000) and you can interact with the swagger on [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Run the API Tests locally

```cmd
pytest
```
