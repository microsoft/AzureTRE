from models.domain.costs import generate_cost_report_dict_example, GranularityEnum, \
    generate_workspace_cost_report_dict_example


def get_cost_report_responses():
    return {
        200: {
            "description": "Success",
            "content": {
                "application/json": {
                    "examples": {
                        "daily": {
                            "summary": "Daily granularity",
                            "description": "each costs array will hold daily aggregation of costs between time period",
                            "value": generate_cost_report_dict_example(GranularityEnum.daily),
                        },
                        "none": {
                            "summary": "No granularity",
                            "description": "each costs array will hold aggregation of costs between time period",
                            "value": generate_cost_report_dict_example(GranularityEnum.none),
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
        },
        429: {
            "description": "Too Many Requests",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "429",
                            "message": "Too many requests to Azure cost management API. Please retry.",
                            "retry-after": "30"
                        }
                    }
                }
            }
        },
        503: {
            "description": "Service Unavailable",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "503",
                            "message": "Azure cost management API is temporarly unavaiable. Please retry.",
                            "retry-after": "30"
                        }
                    }
                }
            }
        }
    }


def get_workspace_cost_report_responses():
    return {
        200: {
            "description": "Success",
            "content": {
                "application/json": {
                    "examples": {
                        "daily": {
                            "summary": "Daily granularity",
                            "description": "Each costs array will hold daily aggregation of costs between time period",
                            "value": generate_workspace_cost_report_dict_example("My Workspace", GranularityEnum.daily),
                        },
                        "none": {
                            "summary": "No granularity",
                            "description": "Each costs array will hold aggregation of costs between time period",
                            "value": generate_workspace_cost_report_dict_example("My Workspace", GranularityEnum.none),
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
        },
        429: {
            "description": "Too Many Requests",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "429",
                            "message": "Too many requests to Azure cost management API. Please retry.",
                            "retry-after": "30"
                        }
                    }
                }
            }
        },
        503: {
            "description": "Service Unavailable",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "503",
                            "message": "Azure cost management API is temporarly unavaiable. Please retry.",
                            "retry-after": "30"
                        }
                    }
                }
            }
        }
    }


def get_mhra_workspace_costs_responses():
    return {
        200: {
            "description": "Success",
            "content": {
                "application/json": {
                    "workspace_costs_items": {
                        "workspace_1": {
                            "partition_key": "None",
                            "row_key": "aa0ef4e2-0b45-4d41-988b-e0ec59e0272e",
                            "workspace_id": "aa0ef4e2-0b45-4d41-988b-e0ec59e0272e",
                            "credit_limit": "1000.0",
                            "available_credit": "300.0",
                            "credit_percentage_usage": "70",
                            "update_time": "1708593415"
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
