# Operation

Operation model

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** | GUID identifying the operation | 
**resource_id** | **str** | GUID identifying the resource | 
**_resource_path** | **str** | Path of the resource undergoing change, i.e. &#39;/workspaces/guid/workspace-services/guid/&#39; | 
**action** | **str** | Name of the action being performed on the resource, i.e. install, uninstall, start | 
**resource_version** | **int** | Version of the resource this operation relates to | [optional]  if omitted the server will use the default value of 0
**status** | **bool, date, datetime, dict, float, int, list, str, none_type** |  | [optional] 
**message** | **str** |  | [optional]  if omitted the server will use the default value of ""
**created_when** | **float** |  | [optional] 
**updated_when** | **float** |  | [optional] 
**user** | **{str: (bool, date, datetime, dict, float, int, list, str, none_type)}** |  | [optional]  if omitted the server will use the default value of {}
**any string name** | **bool, date, datetime, dict, float, int, list, str, none_type** | any string name can be used but the value must be the correct type | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


