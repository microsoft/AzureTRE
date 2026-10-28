"""Make sure that the Gitea web app keeps its secrets out of its console log."""

import asyncio
import re

LOGS = "https://api.loganalytics.io"
LOG_API = "2022-10-01"
WEB_API = "2022-09-01"
SECRET_SETTINGS = ("GITEA_PASSWD", "GITEA_OPENID_CLIENT_SECRET", "GITEA__database__PASSWD")
SITE_ID = re.compile(r"^/subscriptions/[0-9a-f-]+/resourceGroups/[\w.-]+/providers/Microsoft\.Web/sites/[\w-]+$")
# The start script hides the secret values as ***. A line that shows a value, or a new access token, is a leak.
LEAK_QUERY = """AppServiceConsoleLogs
| where _ResourceId =~ '{site_id}'
| summarize started = countif(ResultDescription contains 'Adding admin user'),
    leaks = countif((ResultDescription contains '--password=' and ResultDescription !contains '--password=***')
        or (ResultDescription contains '--secret ' and ResultDescription !contains '--secret ***')
        or ResultDescription contains 'Access token was successfully created')"""


async def key_vault_references(arm, site_id):
    """Return the status of each secret app setting. Azure returns the status only, not the value."""
    statuses = {}
    for name in SECRET_SETTINGS:
        reference = await arm.request("GET", f"{site_id}/config/configreferences/appsettings/{name}", WEB_API)
        statuses[name] = reference["properties"].get("status")
    return statuses


async def console_log_counts(arm, workspace_id, site_id, minutes=15):
    """Count the start lines and the secret lines in the console log. The query returns counts only."""
    if not SITE_ID.match(site_id):
        raise ValueError("Expected a web app resource ID")
    customer_id = (await arm.request("GET", workspace_id, LOG_API))["properties"]["customerId"]
    query = LEAK_QUERY.format(site_id=site_id.lower())
    async with asyncio.timeout(minutes * 60):
        while True:
            token = await asyncio.to_thread(arm.credential.get_token, f"{LOGS}/.default")
            response = await arm.client.post(
                f"{LOGS}/v1/workspaces/{customer_id}/query",
                headers={"Authorization": f"Bearer {token.token}"},
                json={"query": query, "timespan": "P1D"},
            )
            if response.status_code != 200:
                raise RuntimeError(f"Log Analytics query failed with HTTP {response.status_code}")
            table = response.json()["tables"][0]
            counts = dict(zip([column["name"] for column in table["columns"]], table["rows"][0]))
            # Log Analytics can show a line some minutes after the app writes it.
            if counts["started"]:
                return counts
            await asyncio.sleep(60)
