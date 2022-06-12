import os
from typing import Dict
from datetime import date, datetime
import pytz

from azure.identity import DefaultAzureCredential
from azure.mgmt.costmanagement import CostManagementClient
from azure.mgmt.costmanagement.models import QueryGrouping, QueryAggregation, QueryDataset, QueryDefinition, \
    TimeframeType, ExportType, QueryTimePeriod, QueryFilter, QueryComparisonExpression, QueryResult

from api_app.models.domain.costs import GranularityEnum


class CostService:
    scope: str
    client: CostManagementClient

    def __init__(self):
        self.scope = "/subscriptions/{}".format(os.getenv("SUBSCRIPTION_ID"))
        self.client = CostManagementClient(DefaultAzureCredential())

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

    @staticmethod
    def __date_to_datetime(date_to_covert: date):
        converted_datetime = datetime.combine(date_to_covert, datetime.min.time())
        converted_datetime.replace(tzinfo=pytz.UTC)
        return converted_datetime
