from azure.cosmos import CosmosClient
from db.repositories.airlock_requests import AirlockRequestRepository


class AirlockMigration(AirlockRequestRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client)

    def add_created_by_and_rename_in_history(self) -> int:
        num_updated = 0
        for request in self.container.read_all_items():
            # Only migrate if createdBy isn't present
            if 'createdBy' in request:
                continue

            # For each request, check if it has history
            if len(request['history']) > 0:
                # createdBy value will be first user in history
                request['createdBy'] = request['history'][0]['user']

                # Also rename user to updatedBy in each history item
                for item in request['history']:
                    if 'user' in item:
                        item['updatedBy'] = item['user']
                        del item['user']
            else:
                # If not, the createdBy user will be the same as the updatedBy value
                request['createdBy'] = request['updatedBy']

            self.update_item_dict(request)
            num_updated += 1

        return num_updated

    def change_review_resources_to_dict(self) -> int:
        num_updated = 0
        for request in self.container.read_all_items():
            # Only migrate if airlockReviewResources property present and is a list
            if 'reviewUserResources' in request:
                if type(request['reviewUserResources']) == list:
                    updated_review_resources = {}
                    for i, resource in enumerate(request['reviewUserResources']):
                        updated_review_resources['UNKNOWN' + str(i)] = resource

                    request['reviewUserResources'] = updated_review_resources
                    self.update_item_dict(request)
                    num_updated += 1

        return num_updated
