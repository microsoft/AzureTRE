
# TRE API Permissions Map  
These tables specify each endpoint that exists today in TRE API and the permissions it supports.
## Workspace API  
| Endpoints                                                                                                                 | Researcher | Workspace Owner | Airlock Manager |
| ------------------------------------------------------------------------------------------------------------------------- | ---------- | --------------- | --------------- |
| GET /workspaces/{workspace\_id}/workspace-services                                                                        | V          | V               | V               |
| GET /workspaces/{workspace\_id}/workspace-service-templates                                                               | V          | V               | V               |
| GET /workspaces/{workspace\_id}/workspace-service-templates/{service_template_name}/user-resource-templates               | V          | V               | V               |
| GET /workspaces/{workspace\_id}/workspace-services/{service\_id}                                                          | V          | V               |                 |
| POST /workspaces/{workspace\_id}/workspace-services                                                                       | X          | V               |                 |
| PATCH /workspaces/{workspace\_id}/workspace-services/{service\_id}                                                        | X          | V               |                 |
| DELETE /workspaces/{workspace\_id}/workspace-services/{service\_id}                                                       | X          | V               |                 |
| POST /workspaces/{workspace\_id}/workspace-services/{service\_id}/invoke-action                                           | X          | V               |                 |
| GET /workspaces/{workspace\_id}/workspace-services/{service\_id}/operations                                               | X          | V               | V               |
| GET /workspaces/{workspace\_id}/workspace-services/{service\_id}/operations/{operation\_id}                               | X          | V               | V               |
| GET /workspaces/{workspace\_id}/workspace-services/{service\_id}/user-resources                                           | V          | V               | V               |
| GET /workspaces/{workspace\_id}/workspace-services/{service\_id}/user-resources/{resource\_id}                            | V          | V               | V               |
| POST /workspaces/{workspace\_id}/workspace-services/{service\_id}/user-resources                                          | V          | V               | V               |
| PATCH /workspaces/{workspace\_id}/workspace-services/{service\_id}/user-resources/{resource\_id}                          | V          | V               | V               |
| DELETE /workspaces/{workspace\_id}/workspace-services/{service\_id}/user-resources/{resource\_id}                         | V          | V               | V               |
| POST /workspaces/{workspace\_id}/workspace-services/{service\_id}/user-resources/{resource\_id}/invoke-action             | V          | V               | V               |
| GET /workspaces/{workspace\_id}/workspace-services/{service\_id}/user-resources/{resource\_id}/operations                 | V          | V               | V               |
| GET /workspaces/{workspace\_id}/workspace-services/{service\_id}/user-resources/{resource\_id}/operations/{operation\_id} | V          | V               | V               |
| GET /workspaces/{workspace\_id}/requests                                                                                  | V          | V               | V               |
| GET /workspaces/{workspace\_id}/requests/{airlock\_request\_id}                                                           | V          | V               | V               |
| POST /workspaces/{workspace\_id}/requests                                                                                 | V          | V               | X               |
| POST /workspaces/{workspace\_id}/requests/{airlock\_request\_id}/submit                                                   | V          | V               | X               |
| POST /workspaces/{workspace\_id}/requests/{airlock\_request\_id}/cancel                                                   | V          | V               | X               |
| POST /workspaces/{workspace\_id}/requests/{airlock\_request\_id}/review                                                   | X          | X               | V               |
| POST /workspaces/{workspace\_id}/requests/{airlock\_request\_id}/review-user-resource                                                   | X          | X               | V               |
| GET /workspaces/{workspace\_id}/requests/{airlock\_request\_id}/link                                                      | V          | V               | V               |
## Core API  
| Endpoints                                                                                                           | TRE Admin | TRE User | WS Owner |
| ------------------------------------------------------------------------------------------------------------------- | --------- | -------- | -------- |
| GET /workspace-templates                                                                                            | V         | V        |          |
| GET /workspace-templates/{workspace\_template\_name}                                                                | V         | V        |          |
| POST /workspace-templates                                                                                           | V         | X        |          |
| GET /workspace-service-templates                                                                                    | V         | V        |          |
| GET /workspace-service-templates/{workspace\_service\_template\_name}                                               | V         | V        |          |
| POST /workspace-service-templates                                                                                   | V         | X        |          |
| GET /workspace-service-templates/{service\_template\_name}/user-resource-templates                                  | V         | V        |          |
| GET /workspace-service-templates/{service\_template\_name}/user-resource-templates/{user\_resource\_template\_name} | V         | V        |          |
| POST /workspace-service-templates/{service\_template\_name}/user-resource-templates                                 | V         | X        |          |
| GET /workspaces                                                                                                     | V         | V        |          |
| GET /workspaces/(workspace\_id)                                                                                     | V         | V        |          |
| POST /workspaces                                                                                                    | V         | X        |          |
| PATCH /workspaces/{workspace\_id}                                                                                   | V         | X        | X        |
| DELETE /workspaces/{workspace\_id}                                                                                  | V         | X        |  X       |
| POST /workspaces/{workspace\_id}/invoke-action                                                                      | V         | X        |  X       |
| GET /workspaces/{workspace\_id}/operations                                                                          | V         | X        | V        |
| GET /workspaces/{workspace\_id}/operations/{operation\_id}                                                          | V         | X        | V        |
| GET /shared-service-templates                                                                                       | V         | V        |          |
| GET /shared-service-templates/{shared\_service\_template\_name}                                                     | V         | V        |          |
| POST /shared-service-templates                                                                                      | V         | X        |          |
| GET /shared-service                                                                                                 | V         | V        |          |
| GET /shared-service/{shared\_service\_id}                                                                           | V         | V        |          |
| POST /shared-service                                                                                                | V         | X        |          |
| PATCH /shared-service/{shared\_service\_id}                                                                         | V         | X        |          |
| DELETE /shared-service/{shared\_service\_id}                                                                        | V         | X        |          |****
| POST /shared-service/{shared\_service\_id}/invoke-action                                                            | V         | X        |          |
| GET /shared-service/{shared\_service\_id}/operations                                                                | V         | X        |          |
| GET /shared-service/{shared\_service\_id}/operations/{operation\_id}                                                | V         | X        |          |
| POST /migrations                                                                                                    | V         | X        |          |
| GET /costs                                                                                                          | V         | X        | X        |
| GET /workspaces/{workspace\_id}/costs                                                                               | V         | X        | V        |
| GET /health                                                                                                         | \-        | \-       | \-       |
| GET /ping                                                                                                           | \-        | \-       | \-       |
| GET /.metadata                                                                                                      | \-        | \-       | \-       |
