from datetime import datetime, timedelta, date
from typing import List, Optional
from pydantic import BaseModel
import random
import uuid


def generate_cost_row_example():
    return dict({
        "cost": random.uniform(0, 1000), "currency": "USD", "date": (datetime.today() - timedelta(days=-1 * random.randint(0, 1000))).date()
    })


def generate_cost_item_example(name: str):
    return dict(
        id=str(uuid.uuid4()),
        name=name,
        costs=[generate_cost_row_example(), generate_cost_row_example(), generate_cost_row_example()]
    )


def generate_cost_row_stub():
    return CostRow(**generate_cost_row_example())


def generate_cost_item_stub(name: str):
    return CostItem(**dict(
        id=str(uuid.uuid4()),
        name=name,
        costs=[generate_cost_row_stub(), generate_cost_row_stub(), generate_cost_row_stub()]
    ))


def generate_cost_report_example():
    return dict(
        core_services=[generate_cost_row_example()],
        shared_services=[generate_cost_item_example("Gitea"),
                         generate_cost_item_example("Nexus"),
                         generate_cost_item_example("Firewall")],
        workspaces=[generate_cost_item_example("Workspace 1"),
                    generate_cost_item_example("Workspace 2"),
                    generate_cost_item_example("Workspace 3")]
    )


def generate_cost_report_stub():
    return CostReport(**dict(
        core_services=[generate_cost_row_stub()],
        shared_services=[generate_cost_item_stub("Gitea"),
                         generate_cost_item_stub("Nexus"),
                         generate_cost_item_stub("Firewall")],
        workspaces=[generate_cost_item_stub("Workspace 1"),
                    generate_cost_item_stub("Workspace 2"),
                    generate_cost_item_stub("Workspace 3")]
    ))


def generate_workspace_service_cost_report_example(name):
    return dict(
        id=str(uuid.uuid4()),
        name=name,
        costs=[generate_cost_row_example()],
        user_resources=[generate_cost_item_example("VM1"),
                        generate_cost_item_example("VM2"),
                        generate_cost_item_example("VM3")]
    )


def generate_workspace_cost_report_example(name):
    return dict(
        id=str(uuid.uuid4()),
        name=name,
        costs=[generate_cost_row_example()],
        workspace_services=[generate_workspace_service_cost_report_example("Guacamole")]
    )


def generate_workspace_service_cost_report_stub(name):
    return WorkspaceServiceCostItem(**dict(
        id=str(uuid.uuid4()),
        name=name,
        costs=[generate_cost_row_stub()],
        user_resources=[generate_cost_item_stub("VM1"),
                        generate_cost_item_stub("VM2"),
                        generate_cost_item_stub("VM3")]
    ))


def generate_workspace_cost_report_stub(name):
    return WorkspaceCostReport(**dict(
        id=str(uuid.uuid4()),
        name=name,
        costs=[generate_cost_row_stub()],
        workspace_services=[generate_workspace_service_cost_report_stub("Guacamole")]
    ))


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
            "example": generate_cost_report_example()
        }


class WorkspaceServiceCostItem(CostItem):
    user_resources: List[CostItem]


class WorkspaceCostReport(CostItem):
    workspace_services: List[WorkspaceServiceCostItem]

    class Config:
        schema_extra = {
            "example": generate_workspace_cost_report_example("Workspace 1")
        }
