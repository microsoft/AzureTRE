from resources import strings
from db.repositories.airlock_requests import AirlockRequestRepository


class AirlockMigration(AirlockRequestRepository):
    @classmethod
    async def create(cls):
        cls = AirlockMigration()
        resource_repo = await super().create()
        cls._container = resource_repo._container
        return cls

    async def add_created_by_and_rename_in_history(self) -> int:
        num_updated = 0
        for request in await self.query('SELECT * FROM c'):
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

            await self.update_item_dict(request)
            num_updated += 1

        return num_updated

    async def change_review_resources_to_dict(self) -> int:
        num_updated = 0
        for request in await self.query('SELECT * FROM c'):
            # Only migrate if airlockReviewResources property present and is a list
            if 'reviewUserResources' in request:
                if type(request['reviewUserResources']) == list:
                    updated_review_resources = {}
                    for i, resource in enumerate(request['reviewUserResources']):
                        updated_review_resources['UNKNOWN' + str(i)] = resource

                    request['reviewUserResources'] = updated_review_resources
                    await self.update_item_dict(request)
                    num_updated += 1

        return num_updated

    async def update_review_decision_values(self) -> int:
        num_updated = 0
        for request in await self.query('SELECT * FROM c WHERE ARRAY_LENGTH(c.reviews) > 0'):
            request_changed = False

            for review in request['reviews']:
                old_decision = review['reviewDecision']
                new_decision = old_decision

                if old_decision == 'approval_in_progress':
                    new_decision = strings.AIRLOCK_REVIEW_DECISION_APPROVED

                if old_decision == 'rejection_in_progress':
                    new_decision = strings.AIRLOCK_REVIEW_DECISION_REJECTED

                if new_decision != old_decision:
                    request_changed = True
                    review['reviewDecision'] = new_decision

            if request_changed:
                await self.update_item_dict(request)
                num_updated += 1

        return num_updated
