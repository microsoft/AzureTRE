# Collection of API HTTP request samples

This folder contains a set of .http files that can be used to test the API

- [API User Journey](./API%20User%20Journey.http): A typical scenario with registering templates, creating workspaces and other resources
- [API Template GET Endpoints](./API%20Template%20GET%20Endpoints.http)
- [API Template Modifying Endpoints](./API%20Template%20Modifying%20Endpoints.http): POST, DELETE, PATCH endpoints for templates
- [API Resource GET Endpoints](./API%20Resource%20GET%20Endpoints.http)
- [API Resource Modifying Endpoints](API%20Resource%20Modifying%20Endpoints.http): POST, DELETE, PATCH endpoints for workspaces and other resources

## Running the requests in VS Code

1. Install the [Rest Client Extension](https://marketplace.visualstudio.com/items?itemName=humao.rest-client)
1. In settings.json - add a section with environment variables that will be used for the requests

    ```json
        "rest-client.environmentVariables": {
            "$shared": {
                "baseUrl": "http://localhost:8000/api",
                "contentType": "application/json",
                "workspaceTemplate": "my-tre-workspace",
                "workspaceServiceTemplate": "my-tre-workspace-service",
                "userResourceTemplate": "my-tre-user-resource",
                "workspaceId": "49ab7315-49bb-48ed-b9ca-c37369f15e7a",
                "workspaceServiceId": "2a3165e7-5b5c-40e5-b3b6-94f528e9fcf0",
                "userResourceId": "726e00b5-9408-4d81-a913-d890b4851307",
                "appId": "9d52b04f-89cf-47b4-868a-e12be7133b36",
                "token": "[TOKEN FROM SWAGGER UI]"
            },
        },
    ```

    > **Note:** If you prefer, you can add environment specific variables (instead of adding all to $shared, but then you have to change environment in the bottom right bar in VS code when running the HTTP requests)

1. Start the API locally - or modify the baseURL to point to an API running on Azure
1. Authenticate with the API in Swagger and make a GET request to retrieve the authentication token (Bearer) - and modify the token variable in settings
1. Run the requests in the HTTP files by clicking on **send request** above each request

## Running the requests using PyCharms Rest-client

PyCharm has a built in rest client that allows us to run all requests in a .http file.

1. Modify the variables defined in the [http-client.env.json](./http-client.env.json) file to suit your needs
1. Add a file called `http-client.private.env.json` to the API requests folder with the following contents

    ```json
    {
        "dev": {
            "token": "[TOKEN FROM SWAGGER UI]"
        }
    }
    ```

1. Start the API locally or modify the **baseUrl** in `http-client.env.json` to reflect the address of the API you are testing against
1. Make a GET request in Swagger and update the token to your authentication token (Bearer)
1. Run the requests
