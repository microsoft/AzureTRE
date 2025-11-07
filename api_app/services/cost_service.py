from datetime import datetime, date, timedelta
from enum import Enum
from functools import lru_cache
from typing import Dict, Optional, Union
import pandas as pd

from azure.mgmt.costmanagement import CostManagementClient
from azure.mgmt.costmanagement.models import QueryGrouping, QueryAggregation, QueryDataset, QueryDefinition, \
    TimeframeType, ExportType, QueryTimePeriod, QueryFilter, QueryComparisonExpression, QueryResult
from azure.core.exceptions import ResourceNotFoundError, HttpResponseError

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
from services.logging import logger


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


class SubscriptionNotSupported(Exception):
    """Raised when subscription does not support cost management"""


class TooManyRequests(Exception):
    """Raised when cost management api is being throttled, retry after given number of seconds"""
    retry_after: int

    def __init__(self, retry_after: int, *args: object) -> None:
        super().__init__(*args)
        self.retry_after = retry_after


class ServiceUnavailable(Exception):
    """Raised when cost management is unavaiable, retry after given number of seconds"""
    retry_after: int

    def __init__(self, retry_after: int, *args: object) -> None:
        super().__init__(*args)
        self.retry_after = retry_after


class CostCacheItem():
    """Holds cost qery result and time to leave for storing in cache"""
    result: QueryResult
    ttl: datetime

    def __init__(self, item: QueryResult, ttl: datetime) -> None:
        self.result = item
        self.ttl = ttl


# make sure CostService is singleton
@lru_cache(maxsize=None)
class CostService:
    scope: str
    client: CostManagementClient
    cache: Dict[str, CostCacheItem]
    TRE_ID_TAG: str = "tre_id"
    TRE_CORE_SERVICE_ID_TAG: str = "tre_core_service_id"
    TRE_WORKSPACE_ID_TAG: str = "tre_workspace_id"
    TRE_SHARED_SERVICE_ID_TAG: str = "tre_shared_service_id"
    TRE_WORKSPACE_SERVICE_ID_TAG: str = "tre_workspace_service_id"
    TRE_USER_RESOURCE_ID_TAG: str = "tre_user_resource_id"
    TRE_UNTAGGED: str = ""
    RATE_LIMIT_RETRY_AFTER_HEADER_KEY: str = "x-ms-ratelimit-microsoft.costmanagement-entity-retry-after"
    SERVICE_UNAVAILABLE_RETRY_AFTER_HEADER_KEY: str = "Retry-After"

    def __init__(self) -> None:
        self.scope = "/subscriptions/{}".format(config.SUBSCRIPTION_ID)
        self.client = CostManagementClient(credential=credentials.get_credential())
        self.__resource_clients = {}
        self.get_resource_management_client(config.SUBSCRIPTION_ID)
        self.cache = {}

    def get_resource_management_client(self, subscription_id: Optional[str] = None) -> ResourceManagementClient:
        if subscription_id is None:
            subscription_id = config.SUBSCRIPTION_ID

        # Check if resource client is already created for the subscription
        if subscription_id not in self.__resource_clients.keys():
            self.__resource_clients[subscription_id] = ResourceManagementClient(
                credentials.get_credential(),
                subscription_id,
                base_url=config.RESOURCE_MANAGER_ENDPOINT,
                credential_scopes=config.CREDENTIAL_SCOPES
            )
        return self.__resource_clients[subscription_id]

    def get_cached_result(self, key: str) -> Union[QueryResult, None]:
        """Returns cached item result.

        Args:
            key (str): key of the cached item in cache.
        Returns:
            result (Union[QueryResult, None]): cost query result or None if not found or expired.
        """
        cached_item: CostCacheItem = self.cache.get(key, None)

        # return None if key doesn't exist
        if cached_item is None:
            return None

        # return None if key expired
        if (datetime.now() > cached_item.ttl):
            # remove expired cache item
            self.cache.pop(key)
            return None

        return cached_item.result

    def clear_expired_cache_items(self) -> None:
        """Clears all expired cache items."""
        expired_keys = [key for key in self.cache.keys() if datetime.now() > self.cache[key].ttl]
        for key in expired_keys:
            self.cache.pop(key)

    def cache_result(self, key: str, result: QueryResult, timedelta: timedelta) -> None:
        """Add cost result to cache.

        Args:
            key (str) : key of the cached item in cache.
            result (QueryResult) : cost query result to cache.
        """
        self.cache[key] = CostCacheItem(result, datetime.now() + timedelta)
        self.clear_expired_cache_items()

    async def query_tre_costs(self, tre_id, granularity: GranularityEnum, from_date: datetime, to_date: datetime,
                              workspace_repo: WorkspaceRepository,
                              shared_services_repo: SharedServiceRepository) -> CostReport:

        subscription_ids = {config.SUBSCRIPTION_ID}

        #  get all subscription ids from the workspace objects
        subscription_ids.update(await self.__get_workspace_subscription_ids(workspace_repo))

        #  loop through all subscription ids and get resource groups and costs
        resource_groups_dict = {}
        summarized_result = []
        for subscription_id in subscription_ids:
            resource_groups_dict[subscription_id] = self.get_resource_groups_by_tag(self.TRE_ID_TAG, tre_id, subscription_id)

            cache_key = f"{CostService.TRE_ID_TAG}_{tre_id}_granularity{granularity}_from_date{from_date}_to_date{to_date}_subscription{subscription_id}_rgs{'_'.join(list(resource_groups_dict[subscription_id].keys()))}"
            query_result = self.get_cached_result(cache_key)

            if query_result is None:
                query_result = self.query_costs(CostService.TRE_ID_TAG, tre_id, granularity, from_date, to_date, list(resource_groups_dict[subscription_id].keys()), subscription_id)
                self.cache_result(cache_key, query_result, timedelta(hours=2))

            #  append the result to the summarized result
            summarized_result.extend(self.summarize_untagged(query_result, granularity, resource_groups_dict[subscription_id]))

        query_result_dict = self.__query_result_to_dict(summarized_result, granularity)

        cost_report = CostReport(core_services=[], shared_services=[], workspaces=[])

        cost_report.core_services = self.__extract_cost_rows_by_tag(
            granularity, query_result_dict, CostService.TRE_CORE_SERVICE_ID_TAG, tre_id)

        cost_report.shared_services = await self.__get_shared_services_costs(
            granularity, query_result_dict, shared_services_repo)

        cost_report.workspaces = await self.__get_workspaces_costs(granularity, query_result_dict, workspace_repo)

        return cost_report

    async def __get_workspace_subscription_ids(self, workspace_repo: WorkspaceRepository) -> list:
        #  we currently have to query ALL workspace resources to get the subscription ids to calculate costs for
        #  this may be able to change if we store subscriptions in config as per this issue: https://github.com/microsoft/AzureTRE/issues/4528
        workspaces = await workspace_repo.get_active_workspaces()
        subscription_ids = []
        for workspace in workspaces:
            #  check if the property exists and is not empty
            if not workspace.properties.get("workspace_subscription_id"):
                continue
            #  add the subscription id to the set
            subscription_id = workspace.properties["workspace_subscription_id"]
            if subscription_id not in subscription_ids:
                subscription_ids.append(subscription_id)
        return subscription_ids

    async def query_tre_workspace_costs(self, workspace_id: str, granularity: GranularityEnum, from_date: Optional[datetime],
                                        to_date: Optional[datetime],
                                        workspace_repo: WorkspaceRepository,
                                        workspace_services_repo: WorkspaceServiceRepository,
                                        user_resource_repo) -> WorkspaceCostReport:

        resource_groups_dict = self.get_resource_groups_by_tag(self.TRE_WORKSPACE_ID_TAG, workspace_id)

        subscription_id = None

        #  if no resource groups are found with the tag, they may be in another subscription
        #  so we need to get the workspace subscription id and query the resource groups again
        if not resource_groups_dict:
            try:
                workspace = await workspace_repo.get_workspace_by_id(workspace_id)
                subscription_id = workspace.properties["workspace_subscription_id"]
                resource_groups_dict = self.get_resource_groups_by_tag(self.TRE_WORKSPACE_ID_TAG, workspace_id, subscription_id)

            except EntityDoesNotExist:
                raise WorkspaceDoesNotExist(f"workspace_id [{workspace_id}] does not exist")

        cache_key = f"{CostService.TRE_WORKSPACE_ID_TAG}_{workspace_id}_granularity{granularity}_from_date{from_date}_to_date{to_date}_rgs{'_'.join(list(resource_groups_dict.keys()))}"
        query_result = self.get_cached_result(cache_key)

        if query_result is None:
            query_result = self.query_costs(CostService.TRE_WORKSPACE_ID_TAG, workspace_id, granularity, from_date, to_date, list(resource_groups_dict.keys()), subscription_id)
            self.cache_result(cache_key, query_result, timedelta(hours=2))

        summarized_result = self.summarize_untagged(query_result, granularity, resource_groups_dict)
        query_result_dict = self.__query_result_to_dict(summarized_result, granularity)

        try:
            #  check if workspace is already loaded
            if 'workspace' not in locals() or workspace is None:
                workspace = await workspace_repo.get_workspace_by_id(workspace_id)
            workspace_cost_report: WorkspaceCostReport = WorkspaceCostReport(
                id=workspace_id,
                name=self.__get_resource_name(workspace),
                costs=self.__extract_cost_rows_by_tag(granularity, query_result_dict, CostService.TRE_WORKSPACE_ID_TAG,
                                                      workspace_id),
                workspace_services=await self.__get_workspace_services_costs(granularity, query_result_dict,
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

    def get_resource_groups_by_tag(self, tag_name, tag_value, subscription_id: Optional[str] = None) -> dict:

        resource_client = self.get_resource_management_client(subscription_id)
        resource_groups = resource_client.resource_groups.list(filter=f"tagName eq '{tag_name}' and tagValue eq '{tag_value}'")

        return {resouce_group.name: self.extract_resource_group_tag(resouce_group.tags) for resouce_group in resource_groups}

    def summarize_untagged(self, query_result: QueryResult, granularity: GranularityEnum, resource_groups_dict: dict) -> list:
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

        df = df.groupby(c).agg({'PreTaxCost': 'sum'})

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

    async def __get_workspaces_costs(self, granularity, query_result_dict, workspace_repo):
        return [self.__extract_cost_item(workspace, granularity, query_result_dict, CostService.TRE_WORKSPACE_ID_TAG)
                for workspace in await workspace_repo.get_active_workspaces()]

    async def __get_shared_services_costs(self, granularity, query_result_dict, shared_services_repo):
        return [self.__extract_cost_item(shared_service, granularity, query_result_dict,
                                         CostService.TRE_SHARED_SERVICE_ID_TAG)
                for shared_service in await shared_services_repo.get_active_shared_services()]

    async def __get_workspace_services_costs(self, granularity, query_result_dict,
                                             workspace_services_repo: WorkspaceServiceRepository,
                                             user_resource_repo: UserResourceRepository, workspace_id: str):
        workspace_services_costs = []
        workspace_services_list = await workspace_services_repo.get_active_workspace_services_for_workspace(workspace_id)
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
                                                          await user_resource_repo.get_user_resources_for_workspace_service(
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
                    resource_groups: list,
                    subscription_id: Optional[str] = None) -> QueryResult:

        query_definition = self.build_query_definition(granularity, from_date, to_date, tag_name, tag_value, resource_groups)

        scope = "/subscriptions/{}".format(subscription_id) if subscription_id else self.scope
        logger.debug(f"Querying cost management API with scope: {scope} and query definition: {query_definition}")

        try:
            return self.client.query.usage(scope, query_definition)
        except ResourceNotFoundError as e:
            # when cost management API returns 404 with an message:
            # Given subscription {subscription_id} doesn't have valid WebDirect/AIRS offer type.
            # it means that the Azure subscription deosn't support cost management
            if "doesn't have valid WebDirect/AIRS" in e.message:
                logger.exception("Subscription doesn't support cost management")
                raise SubscriptionNotSupported(e)
            else:
                logger.exception("Unhandled Cost Management API error")
                raise e
        except HttpResponseError as e:
            logger.exception("Cost Management API error")
            if e.status_code == 429:
                # Too many requests - Request is throttled.
                # Retry after waiting for the time specified in the "x-ms-ratelimit-microsoft.consumption-retry-after" header.
                if self.RATE_LIMIT_RETRY_AFTER_HEADER_KEY in e.response.headers:
                    raise TooManyRequests(int(e.response.headers[self.RATE_LIMIT_RETRY_AFTER_HEADER_KEY]))
                else:
                    logger.warning(f"{self.RATE_LIMIT_RETRY_AFTER_HEADER_KEY} header was not found in response. Using default retry time of 60 seconds.")
                    raise TooManyRequests(60)  # Default retry after 60 seconds if header is not found
            elif e.status_code == 503:
                # Service unavailable - Service is temporarily unavailable.
                # Retry after waiting for the time specified in the "Retry-After" header.
                if self.SERVICE_UNAVAILABLE_RETRY_AFTER_HEADER_KEY in e.response.headers:
                    raise ServiceUnavailable(int(e.response.headers[self.SERVICE_UNAVAILABLE_RETRY_AFTER_HEADER_KEY]))
                else:
                    logger.exception(f"{self.SERVICE_UNAVAILABLE_RETRY_AFTER_HEADER_KEY} header was not found in response")
                    raise e
            else:
                raise e

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


@lru_cache(maxsize=None)
def cost_service_factory() -> CostService:
    return CostService()
