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
        }
    }
