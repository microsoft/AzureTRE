# UserResourceTemplateInResponse


## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** |  | 
**name** | **str** |  | 
**description** | **str** |  | 
**version** | **str** |  | 
**resource_type** | **bool, date, datetime, dict, float, int, list, str, none_type** |  | 
**current** | **bool** |  | 
**required** | **[str]** |  | 
**properties** | [**{str: (ModelProperty,)}**](ModelProperty.md) |  | 
**system_properties** | [**{str: (ModelProperty,)}**](ModelProperty.md) |  | 
**parent_workspace_service** | **str** | Bundle name | 
**title** | **str** |  | [optional]  if omitted the server will use the default value of ""
**type** | **str** |  | [optional]  if omitted the server will use the default value of "object"
**actions** | [**[CustomAction]**](CustomAction.md) |  | [optional]  if omitted the server will use the default value of []
**custom_actions** | [**[CustomAction]**](CustomAction.md) |  | [optional]  if omitted the server will use the default value of []
**pipeline** | **{str: (bool, date, datetime, dict, float, int, list, str, none_type)}** |  | [optional] 
**additional_properties** | **bool** |  | [optional]  if omitted the server will use the default value of False
**any string name** | **bool, date, datetime, dict, float, int, list, str, none_type** | any string name can be used but the value must be the correct type | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


