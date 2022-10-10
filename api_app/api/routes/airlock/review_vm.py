from models.schemas.operation import OperationInList, OperationInResponse
# TODO:

# - method for creating review VM
# - method for removing review VM

def remove_review_vm(request_id: str) -> OperationInResponse:
    # Find a user resource that has:
    # - template name that is export review vm
    # - request ID property
    # - this request ID as property
    # Issue a delete operation
    review_vm = resource_repo.query(f"SELECT * FROM c WHERE c.templateName = '{template_name}' \
        AND c.properties"

    pass
    # How to watch an operation
    # - decided not to watch an operation, if the delete fails, it will be visible in the UI

# - method for looking up a corresponding workspace
# - method for looking up a corresponding workspace service

