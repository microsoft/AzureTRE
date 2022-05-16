# openapi_client.SharedServiceTemplatesApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**get_shared_service_template_by_name_api_shared_service_templates_shared_service_template_name_get**](SharedServiceTemplatesApi.md#get_shared_service_template_by_name_api_shared_service_templates_shared_service_template_name_get) | **GET** /api/shared-service-templates/{shared_service_template_name} | Get Shared Service Template By Name
[**get_shared_service_templates_api_shared_service_templates_get**](SharedServiceTemplatesApi.md#get_shared_service_templates_api_shared_service_templates_get) | **GET** /api/shared-service-templates | Get Shared Service Templates
[**register_shared_service_template_api_shared_service_templates_post**](SharedServiceTemplatesApi.md#register_shared_service_template_api_shared_service_templates_post) | **POST** /api/shared-service-templates | Register Shared Service Template


# **get_shared_service_template_by_name_api_shared_service_templates_shared_service_template_name_get**
> SharedServiceTemplateInResponse get_shared_service_template_by_name_api_shared_service_templates_shared_service_template_name_get(shared_service_template_name)

Get Shared Service Template By Name

### Example

* OAuth Authentication (oauth2):

```python
import time
import openapi_client
from openapi_client.api import shared_service_templates_api
from openapi_client.model.shared_service_template_in_response import SharedServiceTemplateInResponse
from openapi_client.model.http_validation_error import HTTPValidationError
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
    api_instance = shared_service_templates_api.SharedServiceTemplatesApi(api_client)
    shared_service_template_name = "shared_service_template_name_example" # str | 

    # example passing only required values which don't have defaults set
    try:
        # Get Shared Service Template By Name
        api_response = api_instance.get_shared_service_template_by_name_api_shared_service_templates_shared_service_template_name_get(shared_service_template_name)
        pprint(api_response)
    except openapi_client.ApiException as e:
        print("Exception when calling SharedServiceTemplatesApi->get_shared_service_template_by_name_api_shared_service_templates_shared_service_template_name_get: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **shared_service_template_name** | **str**|  |

### Return type

[**SharedServiceTemplateInResponse**](SharedServiceTemplateInResponse.md)

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

# **get_shared_service_templates_api_shared_service_templates_get**
> ResourceTemplateInformationInList get_shared_service_templates_api_shared_service_templates_get()

Get Shared Service Templates

### Example

* OAuth Authentication (oauth2):

```python
import time
import openapi_client
from openapi_client.api import shared_service_templates_api
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
    api_instance = shared_service_templates_api.SharedServiceTemplatesApi(api_client)

    # example, this endpoint has no required or optional parameters
    try:
        # Get Shared Service Templates
        api_response = api_instance.get_shared_service_templates_api_shared_service_templates_get()
        pprint(api_response)
    except openapi_client.ApiException as e:
        print("Exception when calling SharedServiceTemplatesApi->get_shared_service_templates_api_shared_service_templates_get: %s\n" % e)
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

# **register_shared_service_template_api_shared_service_templates_post**
> SharedServiceTemplateInResponse register_shared_service_template_api_shared_service_templates_post(shared_service_template_in_create)

Register Shared Service Template

### Example

* OAuth Authentication (oauth2):

```python
import time
import openapi_client
from openapi_client.api import shared_service_templates_api
from openapi_client.model.shared_service_template_in_response import SharedServiceTemplateInResponse
from openapi_client.model.http_validation_error import HTTPValidationError
from openapi_client.model.shared_service_template_in_create import SharedServiceTemplateInCreate
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
    api_instance = shared_service_templates_api.SharedServiceTemplatesApi(api_client)
    shared_service_template_in_create = SharedServiceTemplateInCreate(
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
    ) # SharedServiceTemplateInCreate | 

    # example passing only required values which don't have defaults set
    try:
        # Register Shared Service Template
        api_response = api_instance.register_shared_service_template_api_shared_service_templates_post(shared_service_template_in_create)
        pprint(api_response)
    except openapi_client.ApiException as e:
        print("Exception when calling SharedServiceTemplatesApi->register_shared_service_template_api_shared_service_templates_post: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **shared_service_template_in_create** | [**SharedServiceTemplateInCreate**](SharedServiceTemplateInCreate.md)|  |

### Return type

[**SharedServiceTemplateInResponse**](SharedServiceTemplateInResponse.md)

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

