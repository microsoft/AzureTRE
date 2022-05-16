# openapi_client.WorkspaceTemplatesApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**get_workspace_template_by_name_api_workspace_templates_workspace_template_name_get**](WorkspaceTemplatesApi.md#get_workspace_template_by_name_api_workspace_templates_workspace_template_name_get) | **GET** /api/workspace-templates/{workspace_template_name} | Get Workspace Template By Name
[**get_workspace_templates_api_workspace_templates_get**](WorkspaceTemplatesApi.md#get_workspace_templates_api_workspace_templates_get) | **GET** /api/workspace-templates | Get Workspace Templates
[**register_workspace_template_api_workspace_templates_post**](WorkspaceTemplatesApi.md#register_workspace_template_api_workspace_templates_post) | **POST** /api/workspace-templates | Register Workspace Template


# **get_workspace_template_by_name_api_workspace_templates_workspace_template_name_get**
> WorkspaceTemplateInResponse get_workspace_template_by_name_api_workspace_templates_workspace_template_name_get(workspace_template_name)

Get Workspace Template By Name

### Example

* OAuth Authentication (oauth2):

```python
import time
import openapi_client
from openapi_client.api import workspace_templates_api
from openapi_client.model.http_validation_error import HTTPValidationError
from openapi_client.model.workspace_template_in_response import WorkspaceTemplateInResponse
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure OAuth2 access token for authorization: oauth2
configuration = openapi_client.Configuration(
    host = "http://localhost"
)
configuration.access_token = 'YOUR_ACCESS_TOKEN'

# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = workspace_templates_api.WorkspaceTemplatesApi(api_client)
    workspace_template_name = "workspace_template_name_example" # str | 
    is_update = False # bool |  (optional) if omitted the server will use the default value of False

    # example passing only required values which don't have defaults set
    try:
        # Get Workspace Template By Name
        api_response = api_instance.get_workspace_template_by_name_api_workspace_templates_workspace_template_name_get(workspace_template_name)
        pprint(api_response)
    except openapi_client.ApiException as e:
        print("Exception when calling WorkspaceTemplatesApi->get_workspace_template_by_name_api_workspace_templates_workspace_template_name_get: %s\n" % e)

    # example passing only required values which don't have defaults set
    # and optional values
    try:
        # Get Workspace Template By Name
        api_response = api_instance.get_workspace_template_by_name_api_workspace_templates_workspace_template_name_get(workspace_template_name, is_update=is_update)
        pprint(api_response)
    except openapi_client.ApiException as e:
        print("Exception when calling WorkspaceTemplatesApi->get_workspace_template_by_name_api_workspace_templates_workspace_template_name_get: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **workspace_template_name** | **str**|  |
 **is_update** | **bool**|  | [optional] if omitted the server will use the default value of False

### Return type

[**WorkspaceTemplateInResponse**](WorkspaceTemplateInResponse.md)

### Authorization

[oauth2](../README.md#oauth2)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_workspace_templates_api_workspace_templates_get**
> ResourceTemplateInformationInList get_workspace_templates_api_workspace_templates_get()

Get Workspace Templates

### Example

* OAuth Authentication (oauth2):

```python
import time
import openapi_client
from openapi_client.api import workspace_templates_api
from openapi_client.model.resource_template_information_in_list import ResourceTemplateInformationInList
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure OAuth2 access token for authorization: oauth2
configuration = openapi_client.Configuration(
    host = "http://localhost"
)
configuration.access_token = 'YOUR_ACCESS_TOKEN'

# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = workspace_templates_api.WorkspaceTemplatesApi(api_client)

    # example, this endpoint has no required or optional parameters
    try:
        # Get Workspace Templates
        api_response = api_instance.get_workspace_templates_api_workspace_templates_get()
        pprint(api_response)
    except openapi_client.ApiException as e:
        print("Exception when calling WorkspaceTemplatesApi->get_workspace_templates_api_workspace_templates_get: %s\n" % e)
```


### Parameters
This endpoint does not need any parameter.

### Return type

[**ResourceTemplateInformationInList**](ResourceTemplateInformationInList.md)

### Authorization

[oauth2](../README.md#oauth2)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **register_workspace_template_api_workspace_templates_post**
> WorkspaceTemplateInResponse register_workspace_template_api_workspace_templates_post(workspace_template_in_create)

Register Workspace Template

### Example

* OAuth Authentication (oauth2):

```python
import time
import openapi_client
from openapi_client.api import workspace_templates_api
from openapi_client.model.workspace_template_in_create import WorkspaceTemplateInCreate
from openapi_client.model.http_validation_error import HTTPValidationError
from openapi_client.model.workspace_template_in_response import WorkspaceTemplateInResponse
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure OAuth2 access token for authorization: oauth2
configuration = openapi_client.Configuration(
    host = "http://localhost"
)
configuration.access_token = 'YOUR_ACCESS_TOKEN'

# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = workspace_templates_api.WorkspaceTemplatesApi(api_client)
    workspace_template_in_create = WorkspaceTemplateInCreate(
        name="name_example",
        version="version_example",
        current=True,
        json_schema={},
        custom_actions=[
            CustomAction(
                name="name_example",
                description="",
            ),
        ],
    ) # WorkspaceTemplateInCreate | 

    # example passing only required values which don't have defaults set
    try:
        # Register Workspace Template
        api_response = api_instance.register_workspace_template_api_workspace_templates_post(workspace_template_in_create)
        pprint(api_response)
    except openapi_client.ApiException as e:
        print("Exception when calling WorkspaceTemplatesApi->register_workspace_template_api_workspace_templates_post: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **workspace_template_in_create** | [**WorkspaceTemplateInCreate**](WorkspaceTemplateInCreate.md)|  |

### Return type

[**WorkspaceTemplateInResponse**](WorkspaceTemplateInResponse.md)

### Authorization

[oauth2](../README.md#oauth2)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**201** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

