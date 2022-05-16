# openapi_client.HealthApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**get_health_status_api_health_get**](HealthApi.md#get_health_status_api_health_get) | **GET** /api/health | Get Health Status


# **get_health_status_api_health_get**
> bool, date, datetime, dict, float, int, list, str, none_type get_health_status_api_health_get()

Get Health Status

### Example


```python
import time
import openapi_client
from openapi_client.api import health_api
from pprint import pprint
# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient() as api_client:
    # Create an instance of the API class
    api_instance = health_api.HealthApi(api_client)

    # example, this endpoint has no required or optional parameters
    try:
        # Get Health Status
        api_response = api_instance.get_health_status_api_health_get()
        pprint(api_response)
    except openapi_client.ApiException as e:
        print("Exception when calling HealthApi->get_health_status_api_health_get: %s\n" % e)
```


### Parameters
This endpoint does not need any parameter.

### Return type

**bool, date, datetime, dict, float, int, list, str, none_type**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

