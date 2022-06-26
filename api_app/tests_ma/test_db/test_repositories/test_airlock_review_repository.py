from mock import patch
import pytest
from db.repositories.airlock_reviews import AirlockReviewRepository
from models.domain.airlock_review import AirlockReviewDecision
from models.schemas.airlock_review import AirlockReviewInCreate
from models.domain.airlock_resource import AirlockResourceType

WORKSPACE_ID = "abc000d3-82da-4bfc-b6e9-9a7853ef753e"
AIRLOCK_REQUEST_ID = "bbc8cae3-588b-4c7d-b27c-2a5feb7cc646"
AIRLOCK_REVIEW_ID = "76709e9f-5e86-4328-abb1-55d0a380f11e"


@pytest.fixture
def airlock_review_repo():
    with patch('azure.cosmos.CosmosClient') as cosmos_client_mock:
        yield AirlockReviewRepository(cosmos_client_mock)


@pytest.fixture
def sample_airlock_review_input():
    return AirlockReviewInCreate(reviewDecision=AirlockReviewDecision.Approved, decisionExplanation="some decision")


def test_create_airlock_review_item_with_the_right_values(sample_airlock_review_input, airlock_review_repo):
    airlock__review = airlock_review_repo.create_airlock_review_item(sample_airlock_review_input, WORKSPACE_ID, AIRLOCK_REQUEST_ID)

    assert airlock__review.resourceType == AirlockResourceType.AirlockReview
    assert airlock__review.workspaceId == WORKSPACE_ID
    assert airlock__review.requestId == AIRLOCK_REQUEST_ID
    assert airlock__review.reviewDecision == AirlockReviewDecision.Approved
    assert airlock__review.decisionExplanation == "some decision"
