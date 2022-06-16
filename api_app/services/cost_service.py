import os
from random import random
from typing import Dict
from datetime import date, datetime
import pytz
from enum import Enum
from azure.identity import DefaultAzureCredential
from azure.mgmt.costmanagement import CostManagementClient
from azure.mgmt.costmanagement.models import QueryGrouping, QueryAggregation, QueryDataset, QueryDefinition, \
    TimeframeType, ExportType, QueryTimePeriod, QueryFilter, QueryComparisonExpression, QueryResult

from db.repositories.workspaces import WorkspaceRepository
from db.repositories.shared_services import SharedServiceRepository
from db.repositories.workspace_services import WorkspaceServiceRepository
from db.repositories.user_resources import UserResourceRepository
from models.domain.costs import GranularityEnum, WorkspaceCostReport, WorkspaceServiceCostItem, CostReport, \
    CostItem, CostRow
from core import config


class ResultColumnDaily(Enum):
    Cost = 0
    Date = 1
    Tag = 2
    Currency = 3


class ResultColumn(Enum):
    Cost = 0
    Tag = 1
    Currency = 2


class CostService:
    scope: str
    client: CostManagementClient

    def __init__(self):
        self.scope = "/subscriptions/{}".format(config.SUBSCRIPTION_ID)
        self.client = CostManagementClient(DefaultAzureCredential(managed_identity_client_id=config.MANAGED_IDENTITY_CLIENT_ID))

    def query_tre_costs(self, tre_id, granularity: GranularityEnum, from_date: date, to_date: date,
                        workspace_repo: WorkspaceRepository,
                        shared_services_repo: SharedServiceRepository) -> CostReport:

        query_result = self.query_costs("tre_id", tre_id, granularity, from_date, to_date)
        query_result_dict = self.__query_result_to_dict(query_result, granularity)

        cost_report = CostReport(**dict(
            core_services=[],
            shared_services=[],
            workspaces=[]
        ))

        cost_report.core_services = self.__extract_cost_rows(
            granularity, query_result_dict, "tre_core_services_id", tre_id)

        cost_report.shared_services = self.__get_shared_services_costs(
            granularity, query_result_dict, shared_services_repo)

        cost_report.workspaces = self.__get_workspaces_costs(granularity, query_result_dict, workspace_repo)

        return cost_report

    def __get_workspaces_costs(self, granularity, query_result_dict, workspace_repo):
        workspaces_costs = []
        workspaces_list = workspace_repo.get_active_workspaces()
        for workspace in workspaces_list:
            workspace_cost_item = CostItem(**dict(
                id=workspace.id,
                name=workspace.properties["display_name"],
                costs=self.__extract_cost_rows(granularity, query_result_dict, "tre_workspace_id", workspace.id)
            ))
            workspaces_costs.append(workspace_cost_item)
        return workspaces_costs

    def __get_shared_services_costs(self, granularity, query_result_dict, shared_services_repo):
        shared_services_costs = []
        shared_services_list = shared_services_repo.get_active_shared_services()
        for shared_service in shared_services_list:
            shared_service_cost_item = CostItem(**dict(
                id=shared_service.id,
                name=shared_service.properties['display_name'],
                costs=self.__extract_cost_rows(
                    granularity, query_result_dict, "tre_shared_service_id", shared_service.id)
            ))
            shared_services_costs.append(shared_service_cost_item)
        return shared_services_costs

    def __extract_cost_rows(self, granularity, query_result_dict, tag_name, tag_value):
        cost_rows = []
        cost_key = f'"{tag_name}":"{tag_value}"'
        if cost_key in query_result_dict.keys():
            costs = query_result_dict[cost_key]
            if granularity == GranularityEnum.none:
                core_service_cost = costs[0]
                cost_rows.append(CostRow(**dict({
                    "cost": core_service_cost[ResultColumn.Cost.value],
                    "currency": core_service_cost[ResultColumn.Currency.value],
                    "date": None
                })))
            else:
                for core_service_cost in costs:
                    cost_rows.append(CostRow(**dict({
                        "cost": core_service_cost[ResultColumnDaily.Cost.value],
                        "currency": core_service_cost[ResultColumnDaily.Currency.value],
                        "date": core_service_cost[ResultColumnDaily.Date.value]
                    })))

        return cost_rows

    def query_tre_workspace_costs(self, workspace_id: str, granularity: GranularityEnum, from_date: date,
                                  to_date: date,
                                  workspace_repo: WorkspaceRepository,
                                  workspace_services_repo: WorkspaceServiceRepository,
                                  user_resource_repo) -> QueryResult:
        return self.query_costs("tre_workspace_id", workspace_id, granularity, from_date, to_date)

    def query_costs(self, tag_name: str, tag_value: str,
                    granularity: GranularityEnum, from_date: date, to_date: date) -> QueryResult:
        query_definition = self.build_query_definition(from_date, granularity, tag_name, tag_value, to_date)

        return self.client.query.usage(self.scope, query_definition)

    def build_query_definition(self, from_date, granularity, tag_name, tag_value, to_date):
        query_grouping: QueryGrouping = QueryGrouping(name=None, type="Tag")
        query_aggregation: QueryAggregation = QueryAggregation(name="PreTaxCost", function="Sum")
        query_aggregation_dict: Dict[str, QueryAggregation] = dict()
        query_aggregation_dict["totalCost"] = query_aggregation
        query_filter: QueryFilter = QueryFilter(
            tags=QueryComparisonExpression(name=tag_name, operator="In", values=[tag_value]))
        query_grouping_list = list()
        query_grouping_list.append(query_grouping)
        query_dataset: QueryDataset = QueryDataset(
            granularity=granularity, aggregation=query_aggregation_dict,
            grouping=query_grouping_list, filter=query_filter)
        query_time_period: QueryTimePeriod = QueryTimePeriod(
            from_property=self.__date_to_datetime(from_date), to=self.__date_to_datetime(to_date))
        query_definition: QueryDefinition = QueryDefinition(
            type=ExportType.actual_cost, timeframe=TimeframeType.CUSTOM,
            time_period=query_time_period, dataset=query_dataset)
        return query_definition

    def __date_to_datetime(self, date_to_covert: date):
        converted_datetime = datetime.combine(date_to_covert, datetime.min.time())
        converted_datetime.replace(tzinfo=pytz.UTC)
        return converted_datetime

    def __query_result_to_dict(self, query_result: QueryResult, granularity: GranularityEnum):
        query_result_dict = dict()

        for row in query_result.rows:
            tag = row[ResultColumnDaily.Tag.value if granularity == GranularityEnum.daily else ResultColumn.Tag.value]
            if tag in query_result_dict.keys():
                query_result_dict[tag].append(row)
            else:
                query_result_dict[tag] = [row]

        return query_result_dict
