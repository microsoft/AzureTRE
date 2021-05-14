from starlette.config import Config


config = Config(".env")

# api settings
API_PREFIX = "/api"
PROJECT_NAME: str = config("PROJECT_NAME", default="Azure TRE API")
DEBUG: bool = config("DEBUG", cast=bool, default=False)
VERSION = "0.0.0"

# State store configuration
STATE_STORE_ENDPOINT: str = config("STATE_STORE_ENDPOINT", default="")      # cosmos db endpoint
STATE_STORE_KEY: str = config("STATE_STORE_KEY", default="")                # cosmos db access key
