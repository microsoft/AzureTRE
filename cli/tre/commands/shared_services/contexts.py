import click


class SharedServiceContext(object):
    def __init__(self, shared_service_id: str):
        self.shared_service_id = shared_service_id


pass_shared_service_context = click.make_pass_decorator(SharedServiceContext)


class SharedServiceOperationContext(object):
    def __init__(self, shared_service_id: str, operation_id: str):
        self.shared_service_id = shared_service_id
        self.operation_id = operation_id

    @staticmethod
    def add_operation_id_to_context_obj(ctx: click.Context, operation_id: str) -> "SharedServiceOperationContext":
        shared_service_context = ctx.find_object(SharedServiceContext)
        return SharedServiceOperationContext(shared_service_context.shared_service_id, operation_id)


pass_shared_service_operation_context = click.make_pass_decorator(SharedServiceOperationContext)
