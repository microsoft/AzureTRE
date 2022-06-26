import uuid
from azure.cosmos import CosmosClient
from models.domain.airlock_review import AirlockReview
from models.schemas.airlock_review import AirlockReviewInCreate
from db.repositories.airlock_resources import AirlockResourceRepository


class AirlockReviewRepository(AirlockResourceRepository):
    def __init__(self, client: CosmosClient):
        super().__init__(client)

    def create_airlock_review_item(self, airlock_review_input: AirlockReviewInCreate, workspace_id: str, request_id: str) -> AirlockReview:
        full_airlock_review_id = str(uuid.uuid4())

        airlock_review = AirlockReview(
            id=full_airlock_review_id,
            workspaceId=workspace_id,
            requestId=request_id,
            reviewDecision=airlock_review_input.reviewDecision,
            decisionExplanation=airlock_review_input.decisionExplanation
        )

        return airlock_review
