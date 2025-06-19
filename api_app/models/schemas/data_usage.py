def get_workspace_data_usage_responses():
    return {
        200: {
            "description": "Success",
            "content": {
                "application/json": {
                    "workspace_container_usage_items": {
                        "workspace_1": {
                            "partition_key": "None",
                            "row_key": "aa0ef4e2-0b45-4d41-988b-e0ec59e0272e",
                            "workspace_name": "workspace_1",
                            "storage_name": "storage_container_1",
                            "storage_usage": 1.2,
                            "storage_limits": 5000,
                            "storage_limits_update_time": "1708503415",
                            "storage_percentage_used": 20.0,
                            "update_time": "1708593415"
                        }
                    },
                    "workspace_fileshare_usage_items": {
                        "workspace_1": {
                            "partition_key": "None",
                            "row_key": "aa0ef4e2-0b45-4d41-988b-e0ec59e0272e",
                            "workspace_name": "workspace_1",
                            "storage_name": "storage_container_1",
                            "fileshare_usage": 0.0,
                            "fileshare_limits": 5000,
                            "fileshare_limits_update_time": "1708145415",
                            "fileshare_percentage_used": 0.0,
                            "update_time": "1708345415"
                        }
                    }
                }
            }
        },
        401: {
            "description": "Unauthorized",
            "content": {
                "text/plain": {
                    "example": "Not authenticated"
                }
            }
        }
    }


def get_storage_account_limits_responses():
    return {
        200: {
            "description": "Success",
            "content": {
                "application/json": {
                    "storage_account_limits_items": {
                        "workspace_1": {
                            "partition_key": "None",
                            "row_key": "aa0ef4e2-0b45-4d41-988b-e0ec59e0272e",
                            "workspace_name": "workspace_1",
                            "storage_name": "storage_container_1",
                            "storage_limits": 5000,
                            "storage_limits_update_time": "1708503415"
                        },
                        "workspace_2": {
                            "partition_key": "None",
                            "row_key": "b8b8b071-2855-4cfa-8a3a-01b06c615cc4",
                            "workspace_name": "workspace_2",
                            "storage_name": "storage_container_2",
                            "storage_limits": 15000,
                            "storage_limits_update_time": "1708598307"
                        }
                    }
                }
            }
        },
        401: {
            "description": "Unauthorized",
            "content": {
                "text/plain": {
                    "example": "Not authenticated"
                }
            }
        }
    }

def get_storage_info_responses():
    return {
        200: {
            "description": "Success",
            "content": {
                "application/json": {
                    "storage_account_limits_items": {
                        "workspace_1": {
                            "storage_usage": 1.2,
                            "storage_remaining": 1.2,
                            "storage_limits": 5000,
                            "storage_percentage_used": 20.0
                        },
                        "workspace_2": {
                            "storage_usage": 1.2,
                            "storage_remaining": 1.2,
                            "storage_limits": 5000,
                            "storage_percentage_used": 20.0
                        }
                    }
                }
            }
        },
        401: {
            "description": "Unauthorized",
            "content": {
                "text/plain": {
                    "example": "Not authenticated"
                }
            }
        }
    }
