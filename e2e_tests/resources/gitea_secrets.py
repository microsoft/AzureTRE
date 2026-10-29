"""Make sure that the Gitea web app keeps its secrets out of its console log."""

import asyncio
from datetime import timezone
import re
from uuid import uuid4

LOGS = "https://api.loganalytics.io"
LOG_API = "2022-10-01"
WEB_API = "2022-09-01"
SECRET_SETTINGS = ("GITEA_PASSWD", "GITEA_OPENID_CLIENT_SECRET", "GITEA__database__PASSWD")
SITE_ID = re.compile(r"^/subscriptions/[0-9a-f-]+/resourceGroups/[\w.-]+/providers/Microsoft\.Web/sites/[\w-]+$")
# The start script hides the secret values as ***. A line that shows a value, or a new access token, is a leak.
LEAK_QUERY = """AppServiceConsoleLogs
| where _ResourceId =~ '{site_id}'
| summarize started = countif(ResultDescription contains 'Adding admin user'),
    restarted = countif(TimeGenerated >= datetime({since}) and ResultDescription contains 'Configuring OIDC'),
    leaks = countif((ResultDescription contains '--password=' and ResultDescription !contains '--password=***')
        or (ResultDescription contains '--secret ' and ResultDescription !contains '--secret ***')
        or ResultDescription contains 'Access token was successfully created')"""
# The start script writes this line when the OIDC settings change, and then stops Gitea.
OIDC_STOP = "Stopping Gitea, so that it starts again with the new OIDC settings"
OIDC_QUERY = """AppServiceConsoleLogs
| where _ResourceId =~ '{site_id}' and TimeGenerated >= datetime({since})
| summarize stops = countif(ResultDescription contains '{stop}'),
    last_stop = maxif(TimeGenerated, ResultDescription contains '{stop}'),
    last_start = maxif(TimeGenerated, ResultDescription contains 'Configuring OIDC')
| project stops, started_after_stop = iff(isnotnull(last_stop) and isnotnull(last_start) and last_start > last_stop, 1, 0)"""


async def key_vault_references(arm, site_id):
    """Return the status of each secret app setting. Azure returns the status only, not the value."""
    statuses = {}
    for name in SECRET_SETTINGS:
        reference = await arm.request("GET", f"{site_id}/config/configreferences/appsettings/{name}", WEB_API)
        statuses[name] = reference["properties"].get("status")
    return statuses


async def change_oidc_client_id(arm, site_id):
    """Give the web app a new OIDC client ID. A change of the app settings restarts the web app."""
    if not SITE_ID.match(site_id):
        raise ValueError("Expected a web app resource ID")
    # The secret settings are Key Vault references, so the list does not contain a secret value.
    settings = (await arm.request("POST", f"{site_id}/config/appsettings/list", WEB_API))["properties"]
    settings["GITEA_OPENID_CLIENT_ID"] = str(uuid4())
    await arm.request("PUT", f"{site_id}/config/appsettings", WEB_API, body={"properties": settings})


async def wait_for_counts(arm, workspace_id, query, ready, minutes, settle):
    """Run a count query until `ready` accepts the counts. Then wait `settle` seconds and count again."""
    customer_id = (await arm.request("GET", workspace_id, LOG_API))["properties"]["customerId"]

    async def counts():
        token = await asyncio.to_thread(arm.credential.get_token, f"{LOGS}/.default")
        response = await arm.client.post(
            f"{LOGS}/v1/workspaces/{customer_id}/query",
            headers={"Authorization": f"Bearer {token.token}"},
            json={"query": query, "timespan": "P1D"},
        )
        if response.status_code != 200:
            raise RuntimeError(f"Log Analytics query failed with HTTP {response.status_code}")
        table = response.json()["tables"][0]
        return dict(zip([column["name"] for column in table["columns"]], table["rows"][0]))

    async with asyncio.timeout(minutes * 60):
        # Log Analytics can show a line some minutes after the app writes it.
        while not ready(await counts()):
            await asyncio.sleep(60)
    await asyncio.sleep(settle)
    return await counts()


async def console_log_counts(arm, workspace_id, site_id, since, minutes=15, settle=120):
    """Count the start lines and the secret lines in the console log. The query returns counts only.

    Wait for the OIDC line of a start after `since`. Then wait `settle` seconds more, because the lines
    of one start can arrive in Log Analytics at different times.
    """
    if not SITE_ID.match(site_id):
        raise ValueError("Expected a web app resource ID")
    start = since.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    query = LEAK_QUERY.format(site_id=site_id.lower(), since=start)
    return await wait_for_counts(arm, workspace_id, query, lambda counts: counts["restarted"], minutes, settle)


async def oidc_stop_counts(arm, workspace_id, site_id, since, minutes=20, settle=120):
    """Count the stops for new OIDC settings after `since`. Wait for a stop and for a start after it."""
    if not SITE_ID.match(site_id):
        raise ValueError("Expected a web app resource ID")
    start = since.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    query = OIDC_QUERY.format(site_id=site_id.lower(), since=start, stop=OIDC_STOP)
    return await wait_for_counts(
        arm, workspace_id, query, lambda counts: counts["stops"] and counts["started_after_stop"], minutes, settle
    )
