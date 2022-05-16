# openapi_client.SharedServicesApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_a_shared_service_api_shared_services_post**](SharedServicesApi.md#create_a_shared_service_api_shared_services_post) | **POST** /api/shared-services | Create A Shared Service
[**delete_shared_service_api_shared_services_shared_service_id_delete**](SharedServicesApi.md#delete_shared_service_api_shared_services_shared_service_id_delete) | **DELETE** /api/shared-services/{shared_service_id} | Delete Shared Service
[**get_a_single_resource_operation_by_id_api_shared_services_shared_service_id_operations_operation_id_get**](SharedServicesApi.md#get_a_single_resource_operation_by_id_api_shared_services_shared_service_id_operations_operation_id_get) | **GET** /api/shared-services/{shared_service_id}/operations/{operation_id} | Get A Single Resource Operation By Id
[**get_all_operations_for_a_resource_api_shared_services_shared_service_id_operations_get**](SharedServicesApi.md#get_all_operations_for_a_resource_api_shared_services_shared_service_id_operations_get) | **GET** /api/shared-services/{shared_service_id}/operations | Get All Operations For A Resource
[**get_all_shared_services_api_shared_services_get**](SharedServicesApi.md#get_all_shared_services_api_shared_services_get) | **GET** /api/shared-services | Get All Shared Services
[**get_shared_service_by_id_api_shared_services_shared_service_id_get**](SharedServicesApi.md#get_shared_service_by_id_api_shared_services_shared_service_id_get) | **GET** /api/shared-services/{shared_service_id} | Get Shared Service By Id
[**invoke_action_on_a_shared_service_api_shared_services_shared_service_id_invoke_action_post**](SharedServicesApi.md#invoke_action_on_a_shared_service_api_shared_services_shared_service_id_invoke_action_post) | **POST** /api/shared-services/{shared_service_id}/invoke-action | Invoke Action On A Shared Service
[**update_an_existing_shared_service_api_shared_services_shared_service_id_patch**](SharedServicesApi.md#update_an_existing_shared_service_api_shared_services_shared_service_id_patch) | **PATCH** /api/shared-services/{shared_service_id} | Update An Existing Shared Service


# **create_a_shared_service_api_shared_services_post**
> OperationInResponse create_a_shared_service_api_shared_services_post(shared_service_in_create)

Create A Shared Service

### Example

* OAuth Authentication (oauth2):

```python
import time
import openapi_client
from openapi_client.api import shared_services_api
from openapi_client.model.operation_in_response import OperationInResponse
from openapi_client.model.http_validation_error import HTTPValidationError
from openapi_client.model.shared_service_in_create import SharedServiceInCreate
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
    api_instance = shared_services_api.SharedServicesApi(api_client)
    shared_service_in_create = SharedServiceInCreate(
        template_name="template_name_example",
        properties={},
    ) # SharedServiceInCreate | 

    # example passing only required values which don't have defaults set
    try:
        # Create A Shared Service
        api_response = api_instance.create_a_shared_service_api_shared_services_post(shared_service_in_create)
        pprint(api_response)
    except openapi_client.ApiException as e:
        print("Exception when calling SharedServicesApi->create_a_shared_service_api_shared_services_post: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **shared_service_in_create** | [**SharedServiceInCreate**](SharedServiceInCreate.md)|  |

### Return type

[**OperationInResponse**](OperationInResponse.md)

### Authorization

[oauth2](../README.md#oauth2)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**202** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **delete_shared_service_api_shared_services_shared_service_id_delete**
> OperationInResponse delete_shared_service_api_shared_services_shared_service_id_delete(shared_service_id)

Delete Shared Service

### Example

* OAuth Authentication (oauth2):

```python
import time
import openapi_client
from openapi_client.api import shared_services_api
from openapi_client.model.operation_in_response import OperationInResponse
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
    api_instance = shared_services_api.SharedServicesApi(api_client)
    shared_service_id = "shared_service_id_example" # str | 

    # example passing only required values which don't have defaults set
    try:
        # Delete Shared Service
        api_response = api_instance.delete_shared_service_api_shared_services_shared_service_id_delete(shared_service_id)
        pprint(api_response)
    except openapi_client.ApiException as e:
        print("Exception when calling SharedServicesApi->delete_shared_service_api_shared_services_shared_service_id_delete: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **shared_service_id** | **str**|  |

### Return type

[**OperationInResponse**](OperationInResponse.md)

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

# **get_a_single_resource_operation_by_id_api_shared_services_shared_service_id_operations_operation_id_get**
> OperationInResponse get_a_single_resource_operation_by_id_api_shared_services_shared_service_id_operations_operation_id_get(shared_service_id, operation_id)

Get A Single Resource Operation By Id

### Example

* OAuth Authentication (oauth2):

```python
import time
import openapi_client
from openapi_client.api import shared_services_api
from openapi_client.model.operation_in_response import OperationInResponse
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
    api_instance = shared_services_api.SharedServicesApi(api_client)
    shared_service_id = "shared_service_id_example" # str | 
    operation_id = "operation_id_example" # str | 

    # example passing only required values which don't have defaults set
    try:
        # Get A Single Resource Operation By Id
        api_response = api_instance.get_a_single_resource_operation_by_id_api_shared_services_shared_service_id_operations_operation_id_get(shared_service_id, operation_id)
        pprint(api_response)
    except openapi_client.ApiException as e:
        print("Exception when calling SharedServicesApi->get_a_single_resource_operation_by_id_api_shared_services_shared_service_id_operations_operation_id_get: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **shared_service_id** | **str**|  |
 **operation_id** | **str**|  |

### Return type

[**OperationInResponse**](OperationInResponse.md)

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

# **get_all_operations_for_a_resource_api_shared_services_shared_service_id_operations_get**
> OperationInList get_all_operations_for_a_resource_api_shared_services_shared_service_id_operations_get(shared_service_id)

Get All Operations For A Resource

### Example

* OAuth Authentication (oauth2):

```python
import time
import openapi_client
from openapi_client.api import shared_services_api
from openapi_client.model.http_validation_error import HTTPValidationError
from openapi_client.model.operation_in_list import OperationInList
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
    api_instance = shared_services_api.SharedServicesApi(api_client)
    shared_service_id = "shared_service_id_example" # str | 

    # example passing only required values which don't have defaults set
    try:
        # Get All Operations For A Resource
        api_response = api_instance.get_all_operations_for_a_resource_api_shared_services_shared_service_id_operations_get(shared_service_id)
        pprint(api_response)
    except openapi_client.ApiException as e:
        print("Exception when calling SharedServicesApi->get_all_operations_for_a_resource_api_shared_services_shared_service_id_operations_get: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **shared_service_id** | **str**|  |

### Return type

[**OperationInList**](OperationInList.md)

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

# **get_all_shared_services_api_shared_services_get**
> SharedServicesInList get_all_shared_services_api_shared_services_get()

Get All Shared Services

### Example

* OAuth Authentication (oauth2):

```python
import time
import openapi_client
from openapi_client.api import shared_services_api
from openapi_client.model.shared_services_in_list import SharedServicesInList
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
    api_instance = shared_services_api.SharedServicesApi(api_client)

    # example, this endpoint has no required or optional parameters
    try:
        # Get All Shared Services
        api_response = api_instance.get_all_shared_services_api_shared_services_get()
        pprint(api_response)
    except openapi_client.ApiException as e:
        print("Exception when calling SharedServicesApi->get_all_shared_services_api_shared_services_get: %s\n" % e)
```


### Parameters
This endpoint does not need any parameter.

### Return type

[**SharedServicesInList**](SharedServicesInList.md)

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

# **get_shared_service_by_id_api_shared_services_shared_service_id_get**
> SharedServiceInResponse get_shared_service_by_id_api_shared_services_shared_service_id_get(shared_service_id)

Get Shared Service By Id

### Example

* OAuth Authentication (oauth2):

```python
import time
import openapi_client
from openapi_client.api import shared_services_api
from openapi_client.model.http_validation_error import HTTPValidationError
from openapi_client.model.shared_service_in_response import SharedServiceInResponse
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
    api_instance = shared_services_api.SharedServicesApi(api_client)
    shared_service_id = "shared_service_id_example" # str | 

    # example passing only required values which don't have defaults set
    try:
        # Get Shared Service By Id
        api_response = api_instance.get_shared_service_by_id_api_shared_services_shared_service_id_get(shared_service_id)
        pprint(api_response)
    except openapi_client.ApiException as e:
        print("Exception when calling SharedServicesApi->get_shared_service_by_id_api_shared_services_shared_service_id_get: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **shared_service_id** | **str**|  |

### Return type

[**SharedServiceInResponse**](SharedServiceInResponse.md)

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

# **invoke_action_on_a_shared_service_api_shared_services_shared_service_id_invoke_action_post**
> OperationInResponse invoke_action_on_a_shared_service_api_shared_services_shared_service_id_invoke_action_post(shared_service_id, action)

Invoke Action On A Shared Service

### Example

* OAuth Authentication (oauth2):

```python
import time
import openapi_client
from openapi_client.api import shared_services_api
from openapi_client.model.operation_in_response import OperationInResponse
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
    api_instance = shared_services_api.SharedServicesApi(api_client)
    shared_service_id = "shared_service_id_example" # str | 
    action = "action_example" # str | 

    # example passing only required values which don't have defaults set
    try:
        # Invoke Action On A Shared Service
        api_response = api_instance.invoke_action_on_a_shared_service_api_shared_services_shared_service_id_invoke_action_post(shared_service_id, action)
        pprint(api_response)
    except openapi_client.ApiException as e:
        print("Exception when calling SharedServicesApi->invoke_action_on_a_shared_service_api_shared_services_shared_service_id_invoke_action_post: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **shared_service_id** | **str**|  |
 **action** | **str**|  |

### Return type

[**OperationInResponse**](OperationInResponse.md)

### Authorization

[oauth2](../README.md#oauth2)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**202** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **update_an_existing_shared_service_api_shared_services_shared_service_id_patch**
> SharedServiceInResponse update_an_existing_shared_service_api_shared_services_shared_service_id_patch(shared_service_id, resource_patch)

Update An Existing Shared Service

### Example

* OAuth Authentication (oauth2):

```python
import time
import openapi_client
from openapi_client.api import shared_services_api
from openapi_client.model.resource_patch import ResourcePatch
from openapi_client.model.http_validation_error import HTTPValidationError
from openapi_client.model.shared_service_in_response import SharedServiceInResponse
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
    api_instance = shared_services_api.SharedServicesApi(api_client)
    shared_service_id = "shared_service_id_example" # str | 
    resource_patch = ResourcePatch(
        is_enabled=True,
        properties={},
    ) # ResourcePatch | 
    etag = "etag_example" # str |  (optional)

    # example passing only required values which don't have defaults set
    try:
        # Update An Existing Shared Service
        api_response = api_instance.update_an_existing_shared_service_api_shared_services_shared_service_id_patch(shared_service_id, resource_patch)
        pprint(api_response)
    except openapi_client.ApiException as e:
        print("Exception when calling SharedServicesApi->update_an_existing_shared_service_api_shared_services_shared_service_id_patch: %s\n" % e)

    # example passing only required values which don't have defaults set
    # and optional values
    try:
        # Update An Existing Shared Service
        api_response = api_instance.update_an_existing_shared_service_api_shared_services_shared_service_id_patch(shared_service_id, resource_patch, etag=etag)
        pprint(api_response)
    except openapi_client.ApiException as e:
        print("Exception when calling SharedServicesApi->update_an_existing_shared_service_api_shared_services_shared_service_id_patch: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **shared_service_id** | **str**|  |
 **resource_patch** | [**ResourcePatch**](ResourcePatch.md)|  |
 **etag** | **str**|  | [optional]

### Return type

[**SharedServiceInResponse**](SharedServiceInResponse.md)

### Authorization

[oauth2](../README.md#oauth2)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

