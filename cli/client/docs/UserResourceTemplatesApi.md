# openapi_client.UserResourceTemplatesApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**get_user_resource_template_by_name_and_workspace_service_api_workspace_service_templates_service_template_name_user_resource_templates_user_resource_template_name_get**](UserResourceTemplatesApi.md#get_user_resource_template_by_name_and_workspace_service_api_workspace_service_templates_service_template_name_user_resource_templates_user_resource_template_name_get) | **GET** /api/workspace-service-templates/{service_template_name}/user-resource-templates/{user_resource_template_name} | Get User Resource Template By Name And Workspace Service
[**get_user_resource_templates_applicable_to_the_workspace_service_template_api_workspace_service_templates_service_template_name_user_resource_templates_get**](UserResourceTemplatesApi.md#get_user_resource_templates_applicable_to_the_workspace_service_template_api_workspace_service_templates_service_template_name_user_resource_templates_get) | **GET** /api/workspace-service-templates/{service_template_name}/user-resource-templates | Get User Resource Templates Applicable To The Workspace Service Template
[**register_user_resource_template_api_workspace_service_templates_service_template_name_user_resource_templates_post**](UserResourceTemplatesApi.md#register_user_resource_template_api_workspace_service_templates_service_template_name_user_resource_templates_post) | **POST** /api/workspace-service-templates/{service_template_name}/user-resource-templates | Register User Resource Template


# **get_user_resource_template_by_name_and_workspace_service_api_workspace_service_templates_service_template_name_user_resource_templates_user_resource_template_name_get**
> UserResourceTemplateInResponse get_user_resource_template_by_name_and_workspace_service_api_workspace_service_templates_service_template_name_user_resource_templates_user_resource_template_name_get(service_template_name, user_resource_template_name)

Get User Resource Template By Name And Workspace Service

### Example

* OAuth Authentication (oauth2):

```python
import time
import openapi_client
from openapi_client.api import user_resource_templates_api
from openapi_client.model.http_validation_error import HTTPValidationError
from openapi_client.model.user_resource_template_in_response import UserResourceTemplateInResponse
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
    api_instance = user_resource_templates_api.UserResourceTemplatesApi(api_client)
    service_template_name = "service_template_name_example" # str | 
    user_resource_template_name = "user_resource_template_name_example" # str | 
    is_update = False # bool |  (optional) if omitted the server will use the default value of False

    # example passing only required values which don't have defaults set
    try:
        # Get User Resource Template By Name And Workspace Service
        api_response = api_instance.get_user_resource_template_by_name_and_workspace_service_api_workspace_service_templates_service_template_name_user_resource_templates_user_resource_template_name_get(service_template_name, user_resource_template_name)
        pprint(api_response)
    except openapi_client.ApiException as e:
        print("Exception when calling UserResourceTemplatesApi->get_user_resource_template_by_name_and_workspace_service_api_workspace_service_templates_service_template_name_user_resource_templates_user_resource_template_name_get: %s\n" % e)

    # example passing only required values which don't have defaults set
    # and optional values
    try:
        # Get User Resource Template By Name And Workspace Service
        api_response = api_instance.get_user_resource_template_by_name_and_workspace_service_api_workspace_service_templates_service_template_name_user_resource_templates_user_resource_template_name_get(service_template_name, user_resource_template_name, is_update=is_update)
        pprint(api_response)
    except openapi_client.ApiException as e:
        print("Exception when calling UserResourceTemplatesApi->get_user_resource_template_by_name_and_workspace_service_api_workspace_service_templates_service_template_name_user_resource_templates_user_resource_template_name_get: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **service_template_name** | **str**|  |
 **user_resource_template_name** | **str**|  |
 **is_update** | **bool**|  | [optional] if omitted the server will use the default value of False

### Return type

[**UserResourceTemplateInResponse**](UserResourceTemplateInResponse.md)

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

# **get_user_resource_templates_applicable_to_the_workspace_service_template_api_workspace_service_templates_service_template_name_user_resource_templates_get**
> ResourceTemplateInformationInList get_user_resource_templates_applicable_to_the_workspace_service_template_api_workspace_service_templates_service_template_name_user_resource_templates_get(service_template_name)

Get User Resource Templates Applicable To The Workspace Service Template

### Example

* OAuth Authentication (oauth2):

```python
import time
import openapi_client
from openapi_client.api import user_resource_templates_api
from openapi_client.model.http_validation_error import HTTPValidationError
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
    api_instance = user_resource_templates_api.UserResourceTemplatesApi(api_client)
    service_template_name = "service_template_name_example" # str | 

    # example passing only required values which don't have defaults set
    try:
        # Get User Resource Templates Applicable To The Workspace Service Template
        api_response = api_instance.get_user_resource_templates_applicable_to_the_workspace_service_template_api_workspace_service_templates_service_template_name_user_resource_templates_get(service_template_name)
        pprint(api_response)
    except openapi_client.ApiException as e:
        print("Exception when calling UserResourceTemplatesApi->get_user_resource_templates_applicable_to_the_workspace_service_template_api_workspace_service_templates_service_template_name_user_resource_templates_get: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **service_template_name** | **str**|  |

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
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **register_user_resource_template_api_workspace_service_templates_service_template_name_user_resource_templates_post**
> UserResourceTemplateInResponse register_user_resource_template_api_workspace_service_templates_service_template_name_user_resource_templates_post(service_template_name, user_resource_template_in_create)

Register User Resource Template

### Example

* OAuth Authentication (oauth2):

```python
import time
import openapi_client
from openapi_client.api import user_resource_templates_api
from openapi_client.model.http_validation_error import HTTPValidationError
from openapi_client.model.user_resource_template_in_response import UserResourceTemplateInResponse
from openapi_client.model.user_resource_template_in_create import UserResourceTemplateInCreate
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
    api_instance = user_resource_templates_api.UserResourceTemplatesApi(api_client)
    service_template_name = "service_template_name_example" # str | 
    user_resource_template_in_create = UserResourceTemplateInCreate(
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
    ) # UserResourceTemplateInCreate | 

    # example passing only required values which don't have defaults set
    try:
        # Register User Resource Template
        api_response = api_instance.register_user_resource_template_api_workspace_service_templates_service_template_name_user_resource_templates_post(service_template_name, user_resource_template_in_create)
        pprint(api_response)
    except openapi_client.ApiException as e:
        print("Exception when calling UserResourceTemplatesApi->register_user_resource_template_api_workspace_service_templates_service_template_name_user_resource_templates_post: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **service_template_name** | **str**|  |
 **user_resource_template_in_create** | [**UserResourceTemplateInCreate**](UserResourceTemplateInCreate.md)|  |

### Return type

[**UserResourceTemplateInResponse**](UserResourceTemplateInResponse.md)

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

