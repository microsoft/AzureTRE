# SharedService

Shared service request

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** | GUID identifying the resource request | 
**template_name** | **str** | The resource template (bundle) to deploy | 
**template_version** | **str** | The version of the resource template (bundle) to deploy | 
**etag** | **str** | eTag of the document | 
**properties** | **{str: (bool, date, datetime, dict, float, int, list, str, none_type)}** | Parameters for the deployment | [optional]  if omitted the server will use the default value of {}
**is_active** | **bool** |  | [optional]  if omitted the server will use the default value of True
**is_enabled** | **bool** |  | [optional]  if omitted the server will use the default value of True
**resource_type** | **bool, date, datetime, dict, float, int, list, str, none_type** |  | [optional] 
**_resource_path** | **str** |  | [optional]  if omitted the server will use the default value of ""
**resource_version** | **int** |  | [optional]  if omitted the server will use the default value of 0
**user** | **{str: (bool, date, datetime, dict, float, int, list, str, none_type)}** |  | [optional]  if omitted the server will use the default value of {}
**updated_when** | **float** |  | [optional]  if omitted the server will use the default value of 0
**history** | [**[ResourceHistoryItem]**](ResourceHistoryItem.md) |  | [optional]  if omitted the server will use the default value of []
**any string name** | **bool, date, datetime, dict, float, int, list, str, none_type** | any string name can be used but the value must be the correct type | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


