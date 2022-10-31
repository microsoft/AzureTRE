from datetime import datetime, date
from enum import Enum
from typing import Dict, Optional
import pandas as pd

from azure.mgmt.costmanagement import CostManagementClient
from azure.mgmt.costmanagement.models import QueryGrouping, QueryAggregation, QueryDataset, QueryDefinition, \
    TimeframeType, ExportType, QueryTimePeriod, QueryFilter, QueryComparisonExpression, QueryResult

from azure.mgmt.resource import ResourceManagementClient

from core import config, credentials
from db.errors import EntityDoesNotExist
from db.repositories.shared_services import SharedServiceRepository
from db.repositories.user_resources import UserResourceRepository
from db.repositories.workspace_services import WorkspaceServiceRepository
from db.repositories.workspaces import WorkspaceRepository
from models.domain.costs import GranularityEnum, CostReport, WorkspaceCostReport, CostItem, WorkspaceServiceCostItem, \
    CostRow
from models.domain.resource import Resource


class ResultColumnDaily(Enum):
    Cost = 0
    Date = 1
    ResourceGroup = 2
    Tag = 3
    Currency = 4


class ResultColumn(Enum):
    Cost = 0
    ResourceGroup = 1
    Tag = 2
    Currency = 3


class WorkspaceDoesNotExist(Exception):
    """Raised when the workspace is not found by provided id"""


class CostService:
    scope: str
    client: CostManagementClient
    TRE_ID_TAG: str = "tre_id"
    TRE_CORE_SERVICE_ID_TAG: str = "tre_core_service_id"
    TRE_WORKSPACE_ID_TAG: str = "tre_workspace_id"
    TRE_SHARED_SERVICE_ID_TAG: str = "tre_shared_service_id"
    TRE_WORKSPACE_SERVICE_ID_TAG: str = "tre_workspace_service_id"
    TRE_USER_RESOURCE_ID_TAG: str = "tre_user_resource_id"
    TRE_UNTAGGED: str = ""

    def __init__(self):
        self.scope = "/subscriptions/{}".format(config.SUBSCRIPTION_ID)
        self.client = CostManagementClient(credential=credentials.get_credential())
        self.resource_client = ResourceManagementClient(credentials.get_credential(), config.SUBSCRIPTION_ID)

    def query_tre_costs(self, tre_id, granularity: GranularityEnum, from_date: datetime, to_date: datetime,
                        workspace_repo: WorkspaceRepository,
                        shared_services_repo: SharedServiceRepository) -> CostReport:

        resource_groups_dict = self.get_resource_groups_by_tag(self.TRE_ID_TAG, tre_id)

        query_result = self.query_costs(CostService.TRE_ID_TAG, tre_id, granularity, from_date, to_date, list(resource_groups_dict.keys()))

        summerized_result = self.summerize_untagged(query_result, granularity, resource_groups_dict)

        query_result_dict = self.__query_result_to_dict(summerized_result, granularity)

        cost_report = CostReport(core_services=[], shared_services=[], workspaces=[])

        cost_report.core_services = self.__extract_cost_rows_by_tag(
            granularity, query_result_dict, CostService.TRE_CORE_SERVICE_ID_TAG, tre_id)

        cost_report.shared_services = self.__get_shared_services_costs(
            granularity, query_result_dict, shared_services_repo)

        cost_report.workspaces = self.__get_workspaces_costs(granularity, query_result_dict, workspace_repo)

        return cost_report

    def query_tre_workspace_costs(self, workspace_id: str, granularity: GranularityEnum, from_date: Optional[datetime],
                                  to_date: Optional[datetime],
                                  workspace_repo: WorkspaceRepository,
                                  workspace_services_repo: WorkspaceServiceRepository,
                                  user_resource_repo) -> WorkspaceCostReport:

        resource_groups_dict = self.get_resource_groups_by_tag(self.TRE_WORKSPACE_ID_TAG, workspace_id)
        query_result = self.query_costs(CostService.TRE_WORKSPACE_ID_TAG, workspace_id, granularity, from_date, to_date, list(resource_groups_dict.keys()))
        summerized_result = self.summerize_untagged(query_result, granularity, resource_groups_dict)
        query_result_dict = self.__query_result_to_dict(summerized_result, granularity)

        try:
            workspace = workspace_repo.get_workspace_by_id(workspace_id)
            workspace_cost_report: WorkspaceCostReport = WorkspaceCostReport(
                id=workspace_id,
                name=self.__get_resource_name(workspace),
                costs=self.__extract_cost_rows_by_tag(granularity, query_result_dict, CostService.TRE_WORKSPACE_ID_TAG,
                                                      workspace_id),
                workspace_services=self.__get_workspace_services_costs(granularity, query_result_dict,
                                                                       workspace_services_repo,
                                                                       user_resource_repo,
                                                                       workspace_id))

            return workspace_cost_report
        except EntityDoesNotExist:
            raise WorkspaceDoesNotExist(f"workspace_id [{workspace_id}] does not exist")

    def extract_resource_group_tag(self, tags):
        if self.TRE_WORKSPACE_ID_TAG in tags:
            return f'"{self.TRE_WORKSPACE_ID_TAG}":"{tags[self.TRE_WORKSPACE_ID_TAG]}"'
        else:
            return f'"{self.TRE_ID_TAG}":"{tags[self.TRE_ID_TAG]}"'

    def get_resource_groups_by_tag(self, tag_name, tag_value) -> dict:
        resource_groups = self.resource_client.resource_groups.list(filter=f"tagName eq '{tag_name}' and tagValue eq '{tag_value}'")
        return {resouce_group.name: self.extract_resource_group_tag(resouce_group.tags) for resouce_group in resource_groups}

    def summerize_untagged(self, query_result: QueryResult, granularity: GranularityEnum, resource_groups_dict: dict) -> list:
        if len(query_result.rows) == 0:
            return []

        # convert to pandas DataFrame
        df = pd.DataFrame.from_records(query_result.rows)
        columns = []
        for i in range(len(query_result.columns)):
            columns.append(query_result.columns[i].name)
        df.columns = columns

        # fill tags for untagged
        untagged_resource_groups = list(df.loc[df["Tag"] == "", "ResourceGroup"].unique())
        for rg in untagged_resource_groups:
            df.loc[(df["Tag"] == "") & (df["ResourceGroup"] == rg), "Tag"] = resource_groups_dict[rg]

        # group by
        if granularity == GranularityEnum.none:
            c = ["ResourceGroup", "Tag", "Currency"]
        else:
            c = ["UsageDate", "ResourceGroup", "Tag", "Currency"]

        df = df.groupby(c).agg({'PreTaxCost': sum})

        # reset index and reorder columns
        df.reset_index(inplace=True)
        c.insert(0, "PreTaxCost")
        df = df[c]

        # convert to list of rows
        return df.values.tolist()

    def __get_resource_name(self, resource: Resource):
        key = "display_name"
        if key in resource.properties.keys():
            return resource.properties[key]
        else:
            return resource.templateName

    def __extract_cost_item(self, resource: Resource, granularity: GranularityEnum, query_result_dict: dict, tag: str):
        return CostItem(
            id=resource.id,
            name=self.__get_resource_name(resource),
            costs=self.__extract_cost_rows_by_tag(granularity, query_result_dict, tag, resource.id)
        )

    def __get_workspaces_costs(self, granularity, query_result_dict, workspace_repo):
        return [self.__extract_cost_item(workspace, granularity, query_result_dict, CostService.TRE_WORKSPACE_ID_TAG)
                for workspace in workspace_repo.get_active_workspaces()]

    def __get_shared_services_costs(self, granularity, query_result_dict, shared_services_repo):
        return [self.__extract_cost_item(shared_service, granularity, query_result_dict,
                                         CostService.TRE_SHARED_SERVICE_ID_TAG)
                for shared_service in shared_services_repo.get_active_shared_services()]

    def __get_workspace_services_costs(self, granularity, query_result_dict,
                                       workspace_services_repo: WorkspaceServiceRepository,
                                       user_resource_repo: UserResourceRepository, workspace_id: str):
        workspace_services_costs = []
        workspace_services_list = workspace_services_repo.get_active_workspace_services_for_workspace(workspace_id)
        for workspace_service in workspace_services_list:
            workspace_service_cost_item = WorkspaceServiceCostItem(
                id=workspace_service.id,
                name=self.__get_resource_name(workspace_service),
                costs=self.__extract_cost_rows_by_tag(granularity, query_result_dict,
                                                      CostService.TRE_WORKSPACE_SERVICE_ID_TAG,
                                                      workspace_service.id),
                user_resources=[]
            )

            workspace_service_cost_item.user_resources = [self.__extract_cost_item(user_resource,
                                                                                   granularity,
                                                                                   query_result_dict,
                                                                                   CostService.TRE_USER_RESOURCE_ID_TAG)
                                                          for user_resource in
                                                          user_resource_repo.get_user_resources_for_workspace_service(
                                                              workspace_id,
                                                              workspace_service.id)]

            workspace_services_costs.append(workspace_service_cost_item)
        return workspace_services_costs

    def __create_cost_row(self, cost, currency: str, cost_date: date):
        return CostRow(cost=cost, currency=currency, date=cost_date)

    def __extract_cost_rows_by_tag(self, granularity, query_result_dict, tag_name, tag_value):
        cost_rows = []
        cost_key = f'"{tag_name}":"{tag_value}"'
        if cost_key in query_result_dict.keys():
            costs = query_result_dict[cost_key]
            if granularity == GranularityEnum.none:
                cost_rows = [
                    self.__create_cost_row(cost[ResultColumn.Cost.value],
                                           cost[ResultColumn.Currency.value], None) for cost in costs]
            else:
                cost_rows = [
                    self.__create_cost_row(cost[ResultColumnDaily.Cost.value],
                                           cost[ResultColumnDaily.Currency.value],
                                           self.__parse_cost_management_date_value(
                                               cost[ResultColumnDaily.Date.value])) for cost in costs]

        return cost_rows

    def query_costs(self, tag_name: str, tag_value: str,
                    granularity: GranularityEnum, from_date: Optional[datetime],
                    to_date: Optional[datetime],
                    resource_groups: list) -> QueryResult:
        query_definition = self.build_query_definition(granularity, from_date, to_date, tag_name, tag_value, resource_groups)

        return self.client.query.usage(self.scope, query_definition)

    def build_query_definition(self, granularity: GranularityEnum, from_date: Optional[datetime],
                               to_date: Optional[datetime], tag_name: str, tag_value: str, resource_groups: list):
        tag_query_grouping: QueryGrouping = QueryGrouping(name=None, type="Tag")
        rg_query_grouping: QueryGrouping = QueryGrouping(name="ResourceGroup", type="Dimension")

        query_aggregation: QueryAggregation = QueryAggregation(name="PreTaxCost", function="Sum")
        query_aggregation_dict: Dict[str, QueryAggregation] = dict()
        query_aggregation_dict["totalCost"] = query_aggregation
        tag_query_filter: QueryFilter = QueryFilter(
            tags=QueryComparisonExpression(name=tag_name, operator="In", values=[tag_value]))
        rg_query_filter: QueryFilter = QueryFilter(
            dimensions=QueryComparisonExpression(name="ResourceGroup", operator="In", values=resource_groups)
        )
        query_filter: QueryFilter = QueryFilter(or_property=[tag_query_filter, rg_query_filter])
        query_grouping_list = list()
        query_grouping_list.append(rg_query_grouping)
        query_grouping_list.append(tag_query_grouping)
        query_dataset: QueryDataset = QueryDataset(
            granularity=granularity, aggregation=query_aggregation_dict,
            grouping=query_grouping_list, filter=query_filter)
        if from_date is None or to_date is None:
            query_definition: QueryDefinition = QueryDefinition(
                type=ExportType.actual_cost, timeframe=TimeframeType.MONTH_TO_DATE, dataset=query_dataset)
        else:
            query_time_period: QueryTimePeriod = QueryTimePeriod(
                from_property=from_date, to=to_date)
            query_definition: QueryDefinition = QueryDefinition(
                type=ExportType.actual_cost, timeframe=TimeframeType.CUSTOM,
                time_period=query_time_period, dataset=query_dataset)
        return query_definition

    def __query_result_to_dict(self, query_result: list, granularity: GranularityEnum):
        query_result_dict = dict()

        for row in query_result:
            tag = row[ResultColumnDaily.Tag.value if granularity == GranularityEnum.daily else ResultColumn.Tag.value]

            if tag in query_result_dict.keys():
                query_result_dict[tag].append(row)
            else:
                query_result_dict[tag] = [row]

        return query_result_dict

    def __parse_cost_management_date_value(self, date_value: int):
        return datetime.strptime(str(date_value), "%Y%m%d").date()
