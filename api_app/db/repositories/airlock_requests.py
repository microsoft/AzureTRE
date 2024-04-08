import copy
import uuid

from datetime import datetime
from typing import List, Optional
from pydantic import UUID4
from azure.cosmos.exceptions import CosmosResourceNotFoundError, CosmosAccessConditionFailedError
from azure.cosmos.aio import CosmosClient
from fastapi import HTTPException, status
from pydantic import parse_obj_as
from models.domain.authentication import User
from db.errors import EntityDoesNotExist
from models.domain.airlock_request import AirlockFile, AirlockRequest, AirlockRequestStatus, \
    AirlockReview, AirlockReviewDecision, AirlockRequestHistoryItem, AirlockRequestType, AirlockReviewUserResource
from models.schemas.airlock_request import AirlockRequestInCreate, AirlockReviewInCreate, AirlockRequestTriageStatements, AirlockRequestStatisticsStatements, AirlockRequestSafeStatisticsStatements
from core import config
from resources import strings
from db.repositories.base import BaseRepository
import logging


class AirlockRequestRepository(BaseRepository):
    @classmethod
    async def create(cls, client: CosmosClient):
        cls = AirlockRequestRepository()
        await super().create(client, config.STATE_STORE_AIRLOCK_REQUESTS_CONTAINER)
        return cls

    @staticmethod
    def get_resource_base_spec_params():
        return {"tre_id": config.TRE_ID}

    def get_timestamp(self) -> float:
        return datetime.utcnow().timestamp()

    async def update_airlock_request_item(self, original_request: AirlockRequest, new_request: AirlockRequest, updated_by: User, request_properties: dict) -> AirlockRequest:
        history_item = AirlockRequestHistoryItem(
            resourceVersion=original_request.resourceVersion,
            updatedWhen=original_request.updatedWhen,
            updatedBy=original_request.updatedBy,
            properties=request_properties
        )
        new_request.history.append(history_item)

        # now update the request props
        new_request.resourceVersion = new_request.resourceVersion + 1
        new_request.updatedBy = updated_by
        new_request.updatedWhen = self.get_timestamp()

        await self.upsert_item_with_etag(new_request, new_request.etag)
        return new_request

    @staticmethod
    def airlock_requests_query():
        return 'SELECT * FROM c'

    def validate_status_update(self, current_status: AirlockRequestStatus, new_status: AirlockRequestStatus):
        # Cannot change status from approved
        approved_condition = current_status != AirlockRequestStatus.Approved
        # Cannot change status from rejected
        rejected_condition = current_status != AirlockRequestStatus.Rejected
        # Cannot change status from blocked
        blocked_condition = current_status != AirlockRequestStatus.Blocked

        # If approved-in-progress can only be changed to approved
        approved_in_progress_condition = current_status == AirlockRequestStatus.ApprovalInProgress and new_status == AirlockRequestStatus.Approved
        # If rejection-in-progress can only be changed to rejected
        rejected_in_progress_condition = current_status == AirlockRequestStatus.RejectionInProgress and new_status == AirlockRequestStatus.Rejected
        # If blocking-in-progress can only be changed to blocked
        blocking_in_progress_condition = current_status == AirlockRequestStatus.BlockingInProgress and new_status == AirlockRequestStatus.Blocked

        # If draft can only be changed to submitted
        draft_condition = current_status == AirlockRequestStatus.Draft and new_status == AirlockRequestStatus.Submitted
        # If submitted needs to get scanned first, which will change the status to either in-review or blocking-in-progress. but if scanner is disabled, it can go straight to in review
        submit_condition = current_status == AirlockRequestStatus.Submitted and (new_status == AirlockRequestStatus.InReview or new_status == AirlockRequestStatus.BlockingInProgress)
        # If in review can only be changed to either approve in progress or rejected in progress
        in_review_condition = current_status == AirlockRequestStatus.InReview and (new_status == AirlockRequestStatus.ApprovalInProgress or new_status == AirlockRequestStatus.RejectionInProgress)
        # Cancel is allowed only if the request is not actively changing, i.e. it is currently in draft or in review
        cancel_condition = (current_status == AirlockRequestStatus.Draft or current_status == AirlockRequestStatus.InReview) and new_status == AirlockRequestStatus.Cancelled
        # Failed is allowed from any non-final status
        failed_condition = (current_status == AirlockRequestStatus.Draft
                            or current_status == AirlockRequestStatus.Submitted
                            or current_status == AirlockRequestStatus.InReview
                            or current_status == AirlockRequestStatus.ApprovalInProgress
                            or current_status == AirlockRequestStatus.RejectionInProgress
                            or current_status == AirlockRequestStatus.BlockingInProgress) and new_status == AirlockRequestStatus.Failed

        return approved_condition and rejected_condition and blocked_condition and (approved_in_progress_condition or rejected_in_progress_condition or blocking_in_progress_condition or draft_condition or submit_condition or in_review_condition or cancel_condition or failed_condition)

    def create_airlock_request_item(self, airlock_request_input: AirlockRequestInCreate, workspace_id: str, user) -> AirlockRequest:
        full_airlock_request_id = str(uuid.uuid4())

        resource_spec_parameters = {**self.get_airlock_request_spec_params()}

        airlock_request = AirlockRequest(
            id=full_airlock_request_id,
            workspaceId=workspace_id,
            title=airlock_request_input.title,
            businessJustification=airlock_request_input.businessJustification,
            type=airlock_request_input.type,
            createdBy=user,
            createdWhen=datetime.utcnow().timestamp(),
            updatedBy=user,
            updatedWhen=datetime.utcnow().timestamp(),
            properties=resource_spec_parameters,
            reviews=[],
            triageStatements=[],
            statisticsStatements=[],
            safeStatisticsStatements=[]
        )

        return airlock_request

    async def get_airlock_requests(self, workspace_id: str, creator_user_id: Optional[str] = None, type: Optional[AirlockRequestType] = None, status: Optional[AirlockRequestStatus] = None, order_by: Optional[str] = None, order_ascending=True) -> List[AirlockRequest]:
        query = self.airlock_requests_query() + f' WHERE c.workspaceId = "{workspace_id}"'

        # optional filters
        if creator_user_id:
            query += ' AND c.createdBy.id=@user_id'
        if status:
            query += ' AND c.status=@status'
        if type:
            query += ' AND c.type=@type'

        # optional sorting
        if order_by:
            query += ' ORDER BY c.' + order_by
            query += ' ASC' if order_ascending else ' DESC'

        parameters = [
            {"name": "@user_id", "value": creator_user_id},
            {"name": "@status", "value": status},
            {"name": "@type", "value": type},
        ]
        airlock_requests = await self.query(query=query, parameters=parameters)
        return parse_obj_as(List[AirlockRequest], airlock_requests)

    async def get_airlock_request_by_id(self, airlock_request_id: UUID4) -> AirlockRequest:
        try:
            airlock_requests = await self.read_item_by_id(str(airlock_request_id))
        except CosmosResourceNotFoundError:
            raise EntityDoesNotExist
        return parse_obj_as(AirlockRequest, airlock_requests)

    async def update_airlock_request(
            self,
            original_request: AirlockRequest,
            updated_by: User,
            new_status: Optional[AirlockRequestStatus] = None,
            request_files: Optional[List[AirlockFile]] = None,
            status_message: Optional[str] = None,
            airlock_review: Optional[AirlockReview] = None,
            review_user_resource: Optional[AirlockReviewUserResource] = None) -> AirlockRequest:
        updated_request = self._build_updated_request(
            original_request=original_request,
            new_status=new_status,
            request_files=request_files,
            status_message=status_message,
            airlock_review=airlock_review,
            review_user_resource=review_user_resource,
            updated_by=updated_by)
        try:
            db_response = await self.update_airlock_request_item(original_request, updated_request, updated_by, {"previousStatus": original_request.status})
        except CosmosAccessConditionFailedError:
            logging.warning(f"ETag mismatch for request ID: '{original_request.id}'. Retrying.")
            original_request = await self.get_airlock_request_by_id(original_request.id)
            updated_request = self._build_updated_request(original_request=original_request, new_status=new_status, request_files=request_files, status_message=status_message, airlock_review=airlock_review)
            db_response = await self.update_airlock_request_item(original_request, updated_request, updated_by, {"previousStatus": original_request.status})

        return db_response

    def get_airlock_request_spec_params(self):
        return self.get_resource_base_spec_params()

    def create_airlock_review_item(self, airlock_review_input: AirlockReviewInCreate, reviewer: User) -> AirlockReview:
        full_airlock_review_id = str(uuid.uuid4())
        airlock_review_decision_from_bool = AirlockReviewDecision.Approved if airlock_review_input.approval else AirlockReviewDecision.Rejected

        airlock_review = AirlockReview(
            id=full_airlock_review_id,
            dateCreated=self.get_timestamp(),
            reviewDecision=airlock_review_decision_from_bool,
            decisionExplanation=airlock_review_input.decisionExplanation,
            reviewer=reviewer
        )

        return airlock_review

    def _build_updated_request(
            self,
            original_request: AirlockRequest,
            new_status: Optional[AirlockRequestStatus] = None,
            request_files: Optional[List[AirlockFile]] = None,
            status_message: Optional[Optional[str]] = None,
            airlock_review: Optional[AirlockReview] = None,
            review_user_resource: Optional[AirlockReviewUserResource] = None,
            updated_by: Optional[User] = None) -> AirlockRequest:
        updated_request = copy.deepcopy(original_request)

        if new_status is not None:
            self._validate_status_update(current_status=original_request.status, new_status=new_status)
            updated_request.status = new_status

        if status_message is not None:
            updated_request.statusMessage = status_message

        if request_files is not None:
            updated_request.files = request_files

        if airlock_review is not None:
            if updated_request.reviews is None:
                updated_request.reviews = [airlock_review]
            else:
                updated_request.reviews.append(airlock_review)

        if review_user_resource is not None and updated_by is not None:
            updated_request.reviewUserResources[updated_by.id] = review_user_resource

        return updated_request

    def _validate_status_update(self, current_status, new_status):
        if not self.validate_status_update(current_status=current_status, new_status=new_status):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=strings.AIRLOCK_REQUEST_ILLEGAL_STATUS_CHANGE)


    async def save_and_check_triage_statements(self, request: AirlockRequest, airlock_request_triage_statements_input: AirlockRequestTriageStatements) -> AirlockRequest:
        triageStatements = AirlockRequestTriageStatements(
            rdgConsistent=airlock_request_triage_statements_input.rdgConsistent,
            noPatientLevelData=airlock_request_triage_statements_input.noPatientLevelData,
            requestedOutputsClear=airlock_request_triage_statements_input.requestedOutputsClear,
            requestedOutputsStatic=airlock_request_triage_statements_input.requestedOutputsStatic,
            requestedOutputsPermittedFiles=airlock_request_triage_statements_input.requestedOutputsPermittedFiles,
            noHiddenInformation=airlock_request_triage_statements_input.noHiddenInformation
        )

        request.triageStatements.clear()
        request.triageStatements.append(triageStatements)

        await self.update_item(request)
        return request


    async def save_and_check_statistics_statements(self, request: AirlockRequest, airlock_request_statistics_statements_input: AirlockRequestStatisticsStatements) -> AirlockRequest:
        statisticsStatements = AirlockRequestStatisticsStatements(
            codeLists=airlock_request_statistics_statements_input.codeLists,
            safeStatistics=airlock_request_statistics_statements_input.safeStatistics,
            statisticalTests=airlock_request_statistics_statements_input.statisticalTests,
            coefficientsAssociation=airlock_request_statistics_statements_input.coefficientsAssociation,
            shape=airlock_request_statistics_statements_input.shape,
            mode=airlock_request_statistics_statements_input.mode,
            ratios=airlock_request_statistics_statements_input.ratios,
            giniCoefficients=airlock_request_statistics_statements_input.giniCoefficients,
            unsafeStatistics=airlock_request_statistics_statements_input.unsafeStatistics,
            frequencies=airlock_request_statistics_statements_input.frequencies,
            position=airlock_request_statistics_statements_input.position,
            extremeValues=airlock_request_statistics_statements_input.extremeValues,
            linearAggregates=airlock_request_statistics_statements_input.linearAggregates,
            riskRatios=airlock_request_statistics_statements_input.riskRatios,
            survivalTables =airlock_request_statistics_statements_input.survivalTables,
            other =airlock_request_statistics_statements_input.other
        )

        request.statisticsStatements.clear()
        request.statisticsStatements.append(statisticsStatements)

        await self.update_item(request)
        return request


    async def save_and_check_safe_statistics_statements(self, request: AirlockRequest, airlock_request_safe_statistics_statements_input: AirlockRequestSafeStatisticsStatements) -> AirlockRequest:
        safeStatisticsStatements = AirlockRequestSafeStatisticsStatements(
            testConfirmation=airlock_request_safe_statistics_statements_input.testConfirmation,
            coefficientsConfirmation=airlock_request_safe_statistics_statements_input.coefficientsConfirmation,
            residualDegrees=airlock_request_safe_statistics_statements_input.residualDegrees,
            modelNotSaturated=airlock_request_safe_statistics_statements_input.modelNotSaturated,
            regressionNotIncluded=airlock_request_safe_statistics_statements_input.regressionNotIncluded,
            shapeConfirmation=airlock_request_safe_statistics_statements_input.shapeConfirmation,
            standardDeviations=airlock_request_safe_statistics_statements_input.standardDeviations,
            shapeMinFive=airlock_request_safe_statistics_statements_input.shapeMinFive,
            modeConfirmation=airlock_request_safe_statistics_statements_input.modeConfirmation,
            ratiosConfirmation=airlock_request_safe_statistics_statements_input.ratiosConfirmation,
            nRatio=airlock_request_safe_statistics_statements_input.nRatio,
            hRatio=airlock_request_safe_statistics_statements_input.hRatio,
            giniCoefficientsConfirmation=airlock_request_safe_statistics_statements_input.giniCoefficientsConfirmation,
            nGiniCoefficient=airlock_request_safe_statistics_statements_input.nGiniCoefficient,
            coefficientLessThan =airlock_request_safe_statistics_statements_input.coefficientLessThan
        )

        request.safeStatisticsStatements.clear()
        request.safeStatisticsStatements.append(safeStatisticsStatements)

        await self.update_item(request)
        return request
