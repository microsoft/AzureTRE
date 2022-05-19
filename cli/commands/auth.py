from distutils.command.config import config
import click
import msal
import os
import sys
import atexit
import json
from msal import PublicClientApplication

CACHE_FILE = "/tmp/tre_token_cache.json"

# Opening JSON file
config_file = open('config.json')
config = json.load(config_file)

# Set up token cache
cache = msal.SerializableTokenCache()
if os.path.exists(CACHE_FILE):
    cache.deserialize(open(CACHE_FILE, "r").read())
atexit.register(lambda:
                open(CACHE_FILE, "w").write(cache.serialize())
                if cache.has_state_changed else None
                )

# MSAL app
app = PublicClientApplication(
    client_id=config["clientId"],
    authority="https://login.microsoftonline.com/" + config["tenantId"],
    token_cache=cache)


def get_token():
    # Try to get token from the cache
    auth_result = None
    accounts = app.get_accounts()
    if accounts:
        auth_result = app.acquire_token_silent(scopes=[config["scope"]], account=accounts[0])
        return auth_result["access_token"]


def login():
    token = get_token()
    if token is not None:
        click.echo("Cached token found, skipping login")
        return

    flow = app.initiate_device_flow(scopes=[config["scope"]])
    if "user_code" not in flow:
        print("Error: unable to initiate device flow")
        exit(1)

    print(flow["message"])
    sys.stdout.flush()  # Some terminal needs this to ensure the message is shown
    app.acquire_token_by_device_flow(flow)  # By default it will block
    click.echo("Login complete")


def logout():
    try:
        os.remove(CACHE_FILE)
        click.echo("Logout complete")
    except Exception as e:
        pass
