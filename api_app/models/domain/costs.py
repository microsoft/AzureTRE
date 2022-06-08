from datetime import datetime, timedelta, date
from typing import List, Optional
from pydantic import BaseModel
from enum import Enum
import random
import uuid


class GranularityEnum(str, Enum):
    daily = "Daily"
    none = "None"


def generate_cost_row_example(granularity: GranularityEnum):
    return dict({
        "cost": random.uniform(0, 1000), "currency": "USD", "date":
            (datetime.today() - timedelta(
                days=-1 * random.randint(0, 1000))).date() if granularity == GranularityEnum.daily else None
    })


def generate_cost_item_example(name: str, granularity: GranularityEnum):
    cost_item = dict(
        id=str(uuid.uuid4()),
        name=name,
        costs=[generate_cost_row_example(granularity)]
    )

    if granularity == GranularityEnum.daily:
        cost_item["costs"].append(generate_cost_row_example(granularity))
        cost_item["costs"].append(generate_cost_row_example(granularity))

    return cost_item


def generate_cost_row_stub(granularity: GranularityEnum):
    return CostRow(**generate_cost_row_example(granularity))


def generate_cost_item_stub(name: str, granularity: GranularityEnum):
    cost_item = CostItem(**dict(
        id=str(uuid.uuid4()),
        name=name,
        costs=[generate_cost_row_stub(granularity)]
    ))

    if granularity == GranularityEnum.daily:
        cost_item.costs.append(generate_cost_row_stub(granularity))
        cost_item.costs.append(generate_cost_row_stub(granularity))

    return cost_item


def generate_cost_report_example(granularity: GranularityEnum):
    cost_report = dict(
        core_services=[generate_cost_row_example(granularity)],
        shared_services=[generate_cost_item_example("Gitea", granularity),
                         generate_cost_item_example("Nexus", granularity),
                         generate_cost_item_example("Firewall", granularity)],
        workspaces=[generate_cost_item_example("Workspace 1", granularity),
                    generate_cost_item_example("Workspace 2", granularity),
                    generate_cost_item_example("Workspace 3", granularity)]
    )

    if granularity == GranularityEnum.daily:
        cost_report["core_services"].append(generate_cost_row_example(granularity))
        cost_report["core_services"].append(generate_cost_row_example(granularity))

    return cost_report


def generate_cost_report_stub(granularity: GranularityEnum):
    cost_report = CostReport(**dict(
        core_services=[generate_cost_row_stub(granularity)],
        shared_services=[generate_cost_item_stub("Gitea", granularity),
                         generate_cost_item_stub("Nexus", granularity),
                         generate_cost_item_stub("Firewall", granularity)],
        workspaces=[generate_cost_item_stub("Workspace 1", granularity),
                    generate_cost_item_stub("Workspace 2", granularity),
                    generate_cost_item_stub("Workspace 3", granularity)]
    ))

    if granularity == GranularityEnum.daily:
        cost_report.core_services.append(generate_cost_row_stub(granularity))
        cost_report.core_services.append(generate_cost_row_stub(granularity))

    return cost_report


def generate_workspace_service_cost_report_example(name: str, granularity: GranularityEnum):
    cost_report = dict(
        id=str(uuid.uuid4()),
        name=name,
        costs=[generate_cost_row_example(granularity)],
        user_resources=[generate_cost_item_example("VM1", granularity),
                        generate_cost_item_example("VM2", granularity),
                        generate_cost_item_example("VM3", granularity)]
    )

    if granularity == GranularityEnum.daily:
        cost_report["costs"].append(generate_cost_row_example(granularity))
        cost_report["costs"].append(generate_cost_row_example(granularity))

    return cost_report


def generate_workspace_cost_report_example(name: str, granularity: GranularityEnum):
    cost_report = dict(
        id=str(uuid.uuid4()),
        name=name,
        costs=[generate_cost_row_example(granularity)],
        workspace_services=[generate_workspace_service_cost_report_example("Guacamole", granularity)]
    )

    if granularity == GranularityEnum.daily:
        cost_report["costs"].append(generate_cost_row_example(granularity))
        cost_report["costs"].append(generate_cost_row_example(granularity))

    return cost_report


def generate_workspace_service_cost_report_stub(name: str, granularity: GranularityEnum):
    cost_item = WorkspaceServiceCostItem(**dict(
        id=str(uuid.uuid4()),
        name=name,
        costs=[generate_cost_row_stub(granularity)],
        user_resources=[generate_cost_item_stub("VM1", granularity),
                        generate_cost_item_stub("VM2", granularity),
                        generate_cost_item_stub("VM3", granularity)]
    ))

    if granularity == GranularityEnum.daily:
        cost_item.costs.append(generate_cost_row_stub(granularity))
        cost_item.costs.append(generate_cost_row_stub(granularity))

    return cost_item


def generate_workspace_cost_report_stub(name: str, granularity: GranularityEnum):
    cost_report = WorkspaceCostReport(**dict(
        id=str(uuid.uuid4()),
        name=name,
        costs=[generate_cost_row_stub(granularity)],
        workspace_services=[generate_workspace_service_cost_report_stub("Guacamole", granularity)]
    ))

    if granularity == GranularityEnum.daily:
        cost_report.costs.append(generate_cost_row_stub(granularity))
        cost_report.costs.append(generate_cost_row_stub(granularity))

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

    class Config:
        schema_extra = {
            "example": generate_cost_report_example(GranularityEnum.daily),
        }


class WorkspaceServiceCostItem(CostItem):
    user_resources: List[CostItem]


class WorkspaceCostReport(CostItem):
    workspace_services: List[WorkspaceServiceCostItem]

    class Config:
        schema_extra = {
            "example": generate_workspace_cost_report_example("Workspace 1", GranularityEnum.daily)
        }
