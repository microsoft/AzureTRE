# openapi_client.WorkspaceServiceTemplatesApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**get_workspace_service_template_by_name_api_workspace_service_templates_service_template_name_get**](WorkspaceServiceTemplatesApi.md#get_workspace_service_template_by_name_api_workspace_service_templates_service_template_name_get) | **GET** /api/workspace-service-templates/{service_template_name} | Get Workspace Service Template By Name
[**get_workspace_service_templates_api_workspace_service_templates_get**](WorkspaceServiceTemplatesApi.md#get_workspace_service_templates_api_workspace_service_templates_get) | **GET** /api/workspace-service-templates | Get Workspace Service Templates
[**register_workspace_service_template_api_workspace_service_templates_post**](WorkspaceServiceTemplatesApi.md#register_workspace_service_template_api_workspace_service_templates_post) | **POST** /api/workspace-service-templates | Register Workspace Service Template


# **get_workspace_service_template_by_name_api_workspace_service_templates_service_template_name_get**
> WorkspaceServiceTemplateInResponse get_workspace_service_template_by_name_api_workspace_service_templates_service_template_name_get(service_template_name)

Get Workspace Service Template By Name

### Example

* OAuth Authentication (oauth2):

```python
import time
import openapi_client
from openapi_client.api import workspace_service_templates_api
from openapi_client.model.http_validation_error import HTTPValidationError
from openapi_client.model.workspace_service_template_in_response import WorkspaceServiceTemplateInResponse
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
    api_instance = workspace_service_templates_api.WorkspaceServiceTemplatesApi(api_client)
    service_template_name = "service_template_name_example" # str | 
    is_update = False # bool |  (optional) if omitted the server will use the default value of False

    # example passing only required values which don't have defaults set
    try:
        # Get Workspace Service Template By Name
        api_response = api_instance.get_workspace_service_template_by_name_api_workspace_service_templates_service_template_name_get(service_template_name)
        pprint(api_response)
    except openapi_client.ApiException as e:
        print("Exception when calling WorkspaceServiceTemplatesApi->get_workspace_service_template_by_name_api_workspace_service_templates_service_template_name_get: %s\n" % e)

    # example passing only required values which don't have defaults set
    # and optional values
    try:
        # Get Workspace Service Template By Name
        api_response = api_instance.get_workspace_service_template_by_name_api_workspace_service_templates_service_template_name_get(service_template_name, is_update=is_update)
        pprint(api_response)
    except openapi_client.ApiException as e:
        print("Exception when calling WorkspaceServiceTemplatesApi->get_workspace_service_template_by_name_api_workspace_service_templates_service_template_name_get: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **service_template_name** | **str**|  |
 **is_update** | **bool**|  | [optional] if omitted the server will use the default value of False

### Return type

[**WorkspaceServiceTemplateInResponse**](WorkspaceServiceTemplateInResponse.md)

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

# **get_workspace_service_templates_api_workspace_service_templates_get**
> ResourceTemplateInformationInList get_workspace_service_templates_api_workspace_service_templates_get()

Get Workspace Service Templates

### Example

* OAuth Authentication (oauth2):

```python
import time
import openapi_client
from openapi_client.api import workspace_service_templates_api
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
    api_instance = workspace_service_templates_api.WorkspaceServiceTemplatesApi(api_client)

    # example, this endpoint has no required or optional parameters
    try:
        # Get Workspace Service Templates
        api_response = api_instance.get_workspace_service_templates_api_workspace_service_templates_get()
        pprint(api_response)
    except openapi_client.ApiException as e:
        print("Exception when calling WorkspaceServiceTemplatesApi->get_workspace_service_templates_api_workspace_service_templates_get: %s\n" % e)
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

# **register_workspace_service_template_api_workspace_service_templates_post**
> WorkspaceServiceTemplateInResponse register_workspace_service_template_api_workspace_service_templates_post(workspace_service_template_in_create)

Register Workspace Service Template

### Example

* OAuth Authentication (oauth2):

```python
import time
import openapi_client
from openapi_client.api import workspace_service_templates_api
from openapi_client.model.workspace_service_template_in_create import WorkspaceServiceTemplateInCreate
from openapi_client.model.http_validation_error import HTTPValidationError
from openapi_client.model.workspace_service_template_in_response import WorkspaceServiceTemplateInResponse
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
    api_instance = workspace_service_templates_api.WorkspaceServiceTemplatesApi(api_client)
    workspace_service_template_in_create = WorkspaceServiceTemplateInCreate(
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
    ) # WorkspaceServiceTemplateInCreate | 

    # example passing only required values which don't have defaults set
    try:
        # Register Workspace Service Template
        api_response = api_instance.register_workspace_service_template_api_workspace_service_templates_post(workspace_service_template_in_create)
        pprint(api_response)
    except openapi_client.ApiException as e:
        print("Exception when calling WorkspaceServiceTemplatesApi->register_workspace_service_template_api_workspace_service_templates_post: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **workspace_service_template_in_create** | [**WorkspaceServiceTemplateInCreate**](WorkspaceServiceTemplateInCreate.md)|  |

### Return type

[**WorkspaceServiceTemplateInResponse**](WorkspaceServiceTemplateInResponse.md)

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

