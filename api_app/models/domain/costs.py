from datetime import datetime, timedelta, date
from typing import List, Optional
from pydantic import BaseModel
from enum import StrEnum
import random
import uuid


class GranularityEnum(StrEnum):
    daily = "Daily"
    none = "None"


class CurrencyEnum(StrEnum):
    USD = "USD"
    ILS = "ILS"


def generate_cost_row_dict_example(granularity: GranularityEnum, currency: CurrencyEnum):
    return dict({
        "cost": random.uniform(0, 365), "currency": currency, "date":
            (datetime.today() - timedelta(
                days=-1 * random.randint(0, 1000))).date() if granularity == GranularityEnum.daily else None
    })


def generate_cost_item_dict_example(name: str, granularity: GranularityEnum):
    cost_item_dict = dict(
        id=str(uuid.uuid4()),
        name=name,
        costs=[generate_cost_row_dict_example(granularity, CurrencyEnum.USD),
               generate_cost_row_dict_example(granularity, CurrencyEnum.ILS)]
    )

    if granularity == GranularityEnum.daily:
        cost_item_dict["costs"].append(generate_cost_row_dict_example(granularity, CurrencyEnum.USD))
        cost_item_dict["costs"].append(generate_cost_row_dict_example(granularity, CurrencyEnum.USD))
        cost_item_dict["costs"].append(generate_cost_row_dict_example(granularity, CurrencyEnum.ILS))

    return cost_item_dict


def generate_cost_report_dict_example(granularity: GranularityEnum):
    cost_report = dict(
        core_services=[generate_cost_row_dict_example(granularity, CurrencyEnum.USD)],
        shared_services=[generate_cost_item_dict_example("Gitea", granularity),
                         generate_cost_item_dict_example("Nexus", granularity),
                         generate_cost_item_dict_example("Firewall", granularity)],
        workspaces=[generate_cost_item_dict_example("Workspace 1", granularity),
                    generate_cost_item_dict_example("Workspace 2", granularity),
                    generate_cost_item_dict_example("Workspace 3", granularity)]
    )

    if granularity == GranularityEnum.daily:
        cost_report["core_services"].append(generate_cost_row_dict_example(granularity, CurrencyEnum.USD))
        cost_report["core_services"].append(generate_cost_row_dict_example(granularity, CurrencyEnum.ILS))

    return cost_report


def generate_workspace_service_cost_report_dict_example(name: str, granularity: GranularityEnum):
    cost_report = dict(
        id=str(uuid.uuid4()),
        name=name,
        costs=[generate_cost_row_dict_example(granularity, CurrencyEnum.USD)],
        user_resources=[generate_cost_item_dict_example("VM1", granularity),
                        generate_cost_item_dict_example("VM2", granularity),
                        generate_cost_item_dict_example("VM3", granularity)]
    )

    if granularity == GranularityEnum.daily:
        cost_report["costs"].append(generate_cost_row_dict_example(granularity, CurrencyEnum.USD))
        cost_report["costs"].append(generate_cost_row_dict_example(granularity, CurrencyEnum.ILS))

    return cost_report


def generate_workspace_cost_report_dict_example(name: str, granularity: GranularityEnum):
    cost_report = dict(
        id=str(uuid.uuid4()),
        name=name,
        costs=[generate_cost_row_dict_example(granularity, CurrencyEnum.USD)],
        workspace_services=[generate_workspace_service_cost_report_dict_example("Guacamole", granularity)]
    )

    if granularity == GranularityEnum.daily:
        cost_report["costs"].append(generate_cost_row_dict_example(granularity, CurrencyEnum.USD))
        cost_report["costs"].append(generate_cost_row_dict_example(granularity, CurrencyEnum.ILS))

    return cost_report


class CostRow(BaseModel):
    cost: float
    currency: str
    date: Optional[date]


class CostItem(BaseModel):
    id: str
    name: str
    costs: List[CostRow]


class CostReport(BaseModel):
    core_services: List[CostRow]
    shared_services: List[CostItem]
    workspaces: List[CostItem]


class WorkspaceServiceCostItem(CostItem):
    user_resources: List[CostItem]


class WorkspaceCostReport(CostItem):
    workspace_services: List[WorkspaceServiceCostItem]
