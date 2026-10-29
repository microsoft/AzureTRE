"""Check the prerequisites for the private OpenAI lifecycle case."""

from datetime import datetime, timezone
import math
from urllib.parse import parse_qsl, urlsplit

COGNITIVE_API = "2024-10-01"
MODEL = "gpt-5.1 | 2025-11-13"
CAPACITY = 1


async def list_values(arm, resource_id):
    """Read all ARM pages, keeping credentials on the original collection."""
    values, seen, query = [], set(), {}
    for _ in range(100):
        page = await arm.request("GET", resource_id, COGNITIVE_API, query=query)
        if not isinstance(page.get("value"), list):
            raise ValueError("Azure returned an invalid model or quota list")
        values.extend(page["value"])
        link = page.get("nextLink")
        if not link:
            return values
        parsed = urlsplit(link)
        pairs = parse_qsl(parsed.query, keep_blank_values=True)
        query = dict(pairs)
        if (
            parsed.scheme != "https"
            or parsed.netloc != "management.azure.com"
            or parsed.path != resource_id
            or parsed.fragment
            or len(query) != len(pairs)
            or query.get("api-version") != COGNITIVE_API
            or link in seen
        ):
            raise ValueError("Azure returned an invalid model or quota continuation link")
        seen.add(link)
        query.pop("api-version")
    raise ValueError("Azure model or quota list exceeded the page limit")


def unexpired(value, now):
    if value is None:
        return True
    try:
        deadline = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return deadline.tzinfo is not None and deadline > now
    except (ValueError, TypeError, AttributeError):
        return False


def supported_sku(models, now):
    """Match the exact approved model and regional Standard deployment type."""
    name, version = (part.strip() for part in MODEL.split("|"))
    for entry in models:
        model = entry.get("model", {})
        if (
            entry.get("kind") != "OpenAI"
            or entry.get("skuName") != "S0"
            or model.get("format") != "OpenAI"
            or model.get("name") != name
            or model.get("version") != version
            or model.get("lifecycleStatus") != "GenerallyAvailable"
            or model.get("capabilities", {}).get("chatCompletion") != "true"
            or not unexpired(model.get("deprecation", {}).get("inference"), now)
        ):
            continue
        for sku in model.get("skus", []):
            usage = sku.get("usageName", "")
            if (
                sku.get("name") == "Standard"
                and usage
                and "finetune" not in usage.lower()
                and unexpired(sku.get("deprecationDate"), now)
            ):
                return sku
    raise ValueError(f"OpenAI prerequisite failed: {MODEL} has no current regional Standard chat deployment")


def check_capacity(sku, usages):
    capacity = sku.get("capacity", {})
    minimum, maximum, step = capacity.get("minimum", 1), capacity.get("maximum", CAPACITY), capacity.get("step", 1)
    if (
        any(type(value) is not int for value in (minimum, maximum, step))
        or step < 1
        or not minimum <= CAPACITY <= maximum
        or (CAPACITY - minimum) % step
        or ("allowedValues" in capacity and CAPACITY not in capacity["allowedValues"])
    ):
        raise ValueError("OpenAI prerequisite failed: Standard does not support one capacity unit")
    for usage in usages:
        if usage.get("name", {}).get("value") != sku["usageName"]:
            continue
        current, limit = usage.get("currentValue"), usage.get("limit")
        if (
            type(current) not in (int, float)
            or type(limit) not in (int, float)
            or not math.isfinite(current)
            or not math.isfinite(limit)
            or current < 0
            or limit < 0
            or usage.get("unit") != "Count"
            or usage.get("status") in ("Blocked", "InOverage", "Unknown")
        ):
            raise ValueError("OpenAI prerequisite failed: quota values are invalid or blocked")
        if limit - current < CAPACITY:
            raise ValueError("OpenAI prerequisite failed: Standard model quota has no free capacity unit")
        return
    raise ValueError("OpenAI prerequisite failed: the Standard model quota was not returned")


async def check_prerequisites(arm, subscription_id, location):
    collection = f"/subscriptions/{subscription_id}/providers/Microsoft.CognitiveServices/locations/{location}"
    sku = supported_sku(await list_values(arm, collection + "/models"), datetime.now(timezone.utc))
    check_capacity(sku, await list_values(arm, collection + "/usages"))
