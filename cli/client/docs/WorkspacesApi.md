# openapi_client.WorkspacesApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_a_workspace_api_workspaces_post**](WorkspacesApi.md#create_a_workspace_api_workspaces_post) | **POST** /api/workspaces | Create A Workspace
[**delete_workspace_api_workspaces_workspace_id_delete**](WorkspacesApi.md#delete_workspace_api_workspaces_workspace_id_delete) | **DELETE** /api/workspaces/{workspace_id} | Delete Workspace
[**get_a_single_resource_operation_by_id_api_workspaces_workspace_id_operations_operation_id_get**](WorkspacesApi.md#get_a_single_resource_operation_by_id_api_workspaces_workspace_id_operations_operation_id_get) | **GET** /api/workspaces/{workspace_id}/operations/{operation_id} | Get A Single Resource Operation By Id
[**get_all_operations_for_a_resource_api_workspaces_workspace_id_operations_get**](WorkspacesApi.md#get_all_operations_for_a_resource_api_workspaces_workspace_id_operations_get) | **GET** /api/workspaces/{workspace_id}/operations | Get All Operations For A Resource
[**get_all_workspaces_api_workspaces_get**](WorkspacesApi.md#get_all_workspaces_api_workspaces_get) | **GET** /api/workspaces | Get All Workspaces
[**get_workspace_by_id_api_workspaces_workspace_id_get**](WorkspacesApi.md#get_workspace_by_id_api_workspaces_workspace_id_get) | **GET** /api/workspaces/{workspace_id} | Get Workspace By Id
[**invoke_action_on_a_workspace_api_workspaces_workspace_id_invoke_action_post**](WorkspacesApi.md#invoke_action_on_a_workspace_api_workspaces_workspace_id_invoke_action_post) | **POST** /api/workspaces/{workspace_id}/invoke-action | Invoke Action On A Workspace
[**update_an_existing_workspace_api_workspaces_workspace_id_patch**](WorkspacesApi.md#update_an_existing_workspace_api_workspaces_workspace_id_patch) | **PATCH** /api/workspaces/{workspace_id} | Update An Existing Workspace


# **create_a_workspace_api_workspaces_post**
> OperationInResponse create_a_workspace_api_workspaces_post(workspace_in_create)

Create A Workspace

### Example

* OAuth Authentication (oauth2):

```python
import time
import openapi_client
from openapi_client.api import workspaces_api
from openapi_client.model.workspace_in_create import WorkspaceInCreate
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
    api_instance = workspaces_api.WorkspacesApi(api_client)
    workspace_in_create = WorkspaceInCreate(
        template_name="template_name_example",
        properties={},
    ) # WorkspaceInCreate | 

    # example passing only required values which don't have defaults set
    try:
        # Create A Workspace
        api_response = api_instance.create_a_workspace_api_workspaces_post(workspace_in_create)
        pprint(api_response)
    except openapi_client.ApiException as e:
        print("Exception when calling WorkspacesApi->create_a_workspace_api_workspaces_post: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **workspace_in_create** | [**WorkspaceInCreate**](WorkspaceInCreate.md)|  |

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

# **delete_workspace_api_workspaces_workspace_id_delete**
> OperationInResponse delete_workspace_api_workspaces_workspace_id_delete(workspace_id)

Delete Workspace

### Example

* OAuth Authentication (oauth2):

```python
import time
import openapi_client
from openapi_client.api import workspaces_api
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
    api_instance = workspaces_api.WorkspacesApi(api_client)
    workspace_id = "workspace_id_example" # str | 

    # example passing only required values which don't have defaults set
    try:
        # Delete Workspace
        api_response = api_instance.delete_workspace_api_workspaces_workspace_id_delete(workspace_id)
        pprint(api_response)
    except openapi_client.ApiException as e:
        print("Exception when calling WorkspacesApi->delete_workspace_api_workspaces_workspace_id_delete: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **workspace_id** | **str**|  |

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

# **get_a_single_resource_operation_by_id_api_workspaces_workspace_id_operations_operation_id_get**
> OperationInResponse get_a_single_resource_operation_by_id_api_workspaces_workspace_id_operations_operation_id_get(workspace_id, operation_id)

Get A Single Resource Operation By Id

### Example

* OAuth Authentication (oauth2):

```python
import time
import openapi_client
from openapi_client.api import workspaces_api
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
    api_instance = workspaces_api.WorkspacesApi(api_client)
    workspace_id = "workspace_id_example" # str | 
    operation_id = "operation_id_example" # str | 

    # example passing only required values which don't have defaults set
    try:
        # Get A Single Resource Operation By Id
        api_response = api_instance.get_a_single_resource_operation_by_id_api_workspaces_workspace_id_operations_operation_id_get(workspace_id, operation_id)
        pprint(api_response)
    except openapi_client.ApiException as e:
        print("Exception when calling WorkspacesApi->get_a_single_resource_operation_by_id_api_workspaces_workspace_id_operations_operation_id_get: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **workspace_id** | **str**|  |
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

# **get_all_operations_for_a_resource_api_workspaces_workspace_id_operations_get**
> OperationInList get_all_operations_for_a_resource_api_workspaces_workspace_id_operations_get(workspace_id)

Get All Operations For A Resource

### Example

* OAuth Authentication (oauth2):

```python
import time
import openapi_client
from openapi_client.api import workspaces_api
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
    api_instance = workspaces_api.WorkspacesApi(api_client)
    workspace_id = "workspace_id_example" # str | 

    # example passing only required values which don't have defaults set
    try:
        # Get All Operations For A Resource
        api_response = api_instance.get_all_operations_for_a_resource_api_workspaces_workspace_id_operations_get(workspace_id)
        pprint(api_response)
    except openapi_client.ApiException as e:
        print("Exception when calling WorkspacesApi->get_all_operations_for_a_resource_api_workspaces_workspace_id_operations_get: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **workspace_id** | **str**|  |

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

# **get_all_workspaces_api_workspaces_get**
> WorkspacesInList get_all_workspaces_api_workspaces_get()

Get All Workspaces

### Example

* OAuth Authentication (oauth2):

```python
import time
import openapi_client
from openapi_client.api import workspaces_api
from openapi_client.model.workspaces_in_list import WorkspacesInList
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
    api_instance = workspaces_api.WorkspacesApi(api_client)

    # example, this endpoint has no required or optional parameters
    try:
        # Get All Workspaces
        api_response = api_instance.get_all_workspaces_api_workspaces_get()
        pprint(api_response)
    except openapi_client.ApiException as e:
        print("Exception when calling WorkspacesApi->get_all_workspaces_api_workspaces_get: %s\n" % e)
```


### Parameters
This endpoint does not need any parameter.

### Return type

[**WorkspacesInList**](WorkspacesInList.md)

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

# **get_workspace_by_id_api_workspaces_workspace_id_get**
> WorkspaceInResponse get_workspace_by_id_api_workspaces_workspace_id_get(workspace_id)

Get Workspace By Id

### Example

* OAuth Authentication (oauth2):

```python
import time
import openapi_client
from openapi_client.api import workspaces_api
from openapi_client.model.workspace_in_response import WorkspaceInResponse
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
    api_instance = workspaces_api.WorkspacesApi(api_client)
    workspace_id = "workspace_id_example" # str | 

    # example passing only required values which don't have defaults set
    try:
        # Get Workspace By Id
        api_response = api_instance.get_workspace_by_id_api_workspaces_workspace_id_get(workspace_id)
        pprint(api_response)
    except openapi_client.ApiException as e:
        print("Exception when calling WorkspacesApi->get_workspace_by_id_api_workspaces_workspace_id_get: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **workspace_id** | **str**|  |

### Return type

[**WorkspaceInResponse**](WorkspaceInResponse.md)

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

# **invoke_action_on_a_workspace_api_workspaces_workspace_id_invoke_action_post**
> OperationInResponse invoke_action_on_a_workspace_api_workspaces_workspace_id_invoke_action_post(workspace_id, action)

Invoke Action On A Workspace

### Example

* OAuth Authentication (oauth2):

```python
import time
import openapi_client
from openapi_client.api import workspaces_api
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
    api_instance = workspaces_api.WorkspacesApi(api_client)
    workspace_id = "workspace_id_example" # str | 
    action = "action_example" # str | 

    # example passing only required values which don't have defaults set
    try:
        # Invoke Action On A Workspace
        api_response = api_instance.invoke_action_on_a_workspace_api_workspaces_workspace_id_invoke_action_post(workspace_id, action)
        pprint(api_response)
    except openapi_client.ApiException as e:
        print("Exception when calling WorkspacesApi->invoke_action_on_a_workspace_api_workspaces_workspace_id_invoke_action_post: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **workspace_id** | **str**|  |
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

# **update_an_existing_workspace_api_workspaces_workspace_id_patch**
> OperationInResponse update_an_existing_workspace_api_workspaces_workspace_id_patch(workspace_id, resource_patch)

Update An Existing Workspace

### Example

* OAuth Authentication (oauth2):

```python
import time
import openapi_client
from openapi_client.api import workspaces_api
from openapi_client.model.resource_patch import ResourcePatch
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
    api_instance = workspaces_api.WorkspacesApi(api_client)
    workspace_id = "workspace_id_example" # str | 
    resource_patch = ResourcePatch(
        is_enabled=True,
        properties={},
    ) # ResourcePatch | 
    etag = "etag_example" # str |  (optional)

    # example passing only required values which don't have defaults set
    try:
        # Update An Existing Workspace
        api_response = api_instance.update_an_existing_workspace_api_workspaces_workspace_id_patch(workspace_id, resource_patch)
        pprint(api_response)
    except openapi_client.ApiException as e:
        print("Exception when calling WorkspacesApi->update_an_existing_workspace_api_workspaces_workspace_id_patch: %s\n" % e)

    # example passing only required values which don't have defaults set
    # and optional values
    try:
        # Update An Existing Workspace
        api_response = api_instance.update_an_existing_workspace_api_workspaces_workspace_id_patch(workspace_id, resource_patch, etag=etag)
        pprint(api_response)
    except openapi_client.ApiException as e:
        print("Exception when calling WorkspacesApi->update_an_existing_workspace_api_workspaces_workspace_id_patch: %s\n" % e)
```


### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **workspace_id** | **str**|  |
 **resource_patch** | [**ResourcePatch**](ResourcePatch.md)|  |
 **etag** | **str**|  | [optional]

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

