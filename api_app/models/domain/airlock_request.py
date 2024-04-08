from enum import Enum
from typing import List, Dict

from models.domain.azuretremodel import AzureTREModel
from pydantic import Field, validator
from pydantic.schema import Optional
from resources import strings


class AirlockRequestStatus(str, Enum):
    """
    Airlock Resource status
    """
    Draft = strings.AIRLOCK_RESOURCE_STATUS_DRAFT
    Submitted = strings.AIRLOCK_RESOURCE_STATUS_SUBMITTED
    InReview = strings.AIRLOCK_RESOURCE_STATUS_INREVIEW
    ApprovalInProgress = strings.AIRLOCK_RESOURCE_STATUS_APPROVAL_INPROGRESS
    Approved = strings.AIRLOCK_RESOURCE_STATUS_APPROVED
    RejectionInProgress = strings.AIRLOCK_RESOURCE_STATUS_REJECTION_INPROGRESS
    Rejected = strings.AIRLOCK_RESOURCE_STATUS_REJECTED
    Cancelled = strings.AIRLOCK_RESOURCE_STATUS_CANCELLED

    Blocked = strings.AIRLOCK_RESOURCE_STATUS_BLOCKED
    BlockingInProgress = strings.AIRLOCK_RESOURCE_STATUS_BLOCKING_INPROGRESS
    Failed = strings.AIRLOCK_RESOURCE_STATUS_FAILED


class AirlockRequestType(str, Enum):
    Import = strings.AIRLOCK_REQUEST_TYPE_IMPORT
    Export = strings.AIRLOCK_REQUEST_TYPE_EXPORT


class AirlockActions(str, Enum):
    Review = strings.AIRLOCK_ACTION_REVIEW
    Cancel = strings.AIRLOCK_ACTION_CANCEL
    Submit = strings.AIRLOCK_ACTION_SUBMIT


class AirlockFile(AzureTREModel):
    name: str = Field(title="name", description="name of the file")
    size: float = Field(title="size", description="size of the file in bytes")


class AirlockReviewDecision(str, Enum):
    Approved = strings.AIRLOCK_REVIEW_DECISION_APPROVED
    Rejected = strings.AIRLOCK_REVIEW_DECISION_REJECTED


class AirlockReview(AzureTREModel):
    """
    Airlock review
    """
    id: str = Field(title="Id", description="GUID identifying the review")
    reviewer: dict = {}
    dateCreated: float = 0
    reviewDecision: AirlockReviewDecision = Field("", title="Airlock review decision")
    decisionExplanation: str = Field(False, title="Explanation why the request was approved/rejected")


class AirlockRequestHistoryItem(AzureTREModel):
    """
    Resource History Item - to preserve history of resource properties
    """
    resourceVersion: int
    updatedWhen: float
    updatedBy: dict = {}
    properties: dict = {}


class AirlockReviewUserResource(AzureTREModel):
    """
    User resource created for Airlock Review
    """
    workspaceId: str = Field(title="Workspace ID")
    workspaceServiceId: str = Field(title="Workspace Service ID")
    userResourceId: str = Field(title="User Resource ID")


class AirlockRequestTriageStatements(AzureTREModel):
    """
    MHRA's specific triage user statements for Export requests
    """
    rdgConsistent: bool = Field("", title="Statement 1", description="Requested outputs are consistent with the RDG approved protocol associated with this workspace.")
    noPatientLevelData: bool = Field("", title="Statement 2", description="No event or patient level data are included in the requested outputs.")
    requestedOutputsClear: bool = Field("", title="Statement 3", description="All requested outputs are sufficiently clear and comprehensible to permit output checking without the need for dataset- or project-specific knowledge.")
    requestedOutputsStatic: bool = Field("", title="Statement 4", description="All requested outputs are static.")
    requestedOutputsPermittedFiles: bool = Field("", title="Statement 5", description="All requested outputs use permitted file types.")
    noHiddenInformation: bool = Field("", title="Statement 6", description="No hidden information has been included (e.g., embedded files), comments, track changes).")


class AirlockRequestContactTeamForm(AzureTREModel):
    """
    MHRA's specific fields for sending messages to Contact Team
    """
    requiredDisclosureAlignment: str = Field("Question 1", title="Why are outputs required that do not align with the disclosure control rules?")
    measuresTakenMinimiseDisclosure: str = Field("Question 2", title="What measures have been taken to minimise the risk of potentially disclosive outputs?")
    transferToThirdParty: str = Field("Question 3", title="Will the outputs be transferred to any other third party?")


class AirlockRequestUnsafeStatisticsStatements(AzureTREModel):
    """
    MHRA's specific details for unsafe statitics
    """
    requestedOutputsStatisticsPosition: bool = Field("", title="Statement 1", description="You stated that your requested outputs include statistics of position. Please confirm the numbers for each group (and complementary groups) are ≥5.")
    requestedOutputsLinearAggregates: bool = Field("", title="Statement 2", description="You stated that your requested outputs include linear aggregates.")
    linearAggregatesDerivedGroups: bool = Field("", title="Statement 3", description="The linear aggregates have been derived from groups containing ≥5 patients or GP practices.")
    pRatioDominanceRule: bool = Field("", title="Statement 4", description="The P-ratio dominance rule has been calculated and is greater than 10%. (NB: ACRO will check this automatically).")
    nkDominanceRule: bool = Field("", title="Statement 5", description="The N-K dominance rule has been calculated for the 2 largest values and is less than 90%. (NB: ACRO will check this automatically).")


class AirlockRequestOtherStatisticsStatements(AzureTREModel):
    """
    MHRA's specific details for other statitics
    """
    requestedOutputsIncludeFrequencies: bool = Field("", title="Statement 1", description="You stated that your requested outputs include frequencies. Please confirm the following.")
    smallFrequenciesSuppressed: bool = Field("", title="Statement 2", description="All counts <5 and frequencies derived from groups containing <5 patients or GP practices have been suppressed.")
    zerosFullCells: bool = Field("", title="Statement 3", description="All zeroes and full cells (100%) are evidential or structural (i.e., something you would expect).")
    underlyingValuesIndependent: bool = Field("", title="Statement 4", description="Underlying values are genuinely independent (i.e., they do not come from the same patient, the patients do not all have the same family number and do not all come from the same GP practice).")
    categoriesComprehensiveData: bool = Field("", title="Statement 5", description="The categories are comprehensive and apply to all data (i.e., all categories of each categorical variable are presented).")
    requestedOutputsExtremeValues: bool = Field("", title="Statement 6", description="You stated that your requested outputs include extreme values. Please confirm the maximum or minimum presented are non-informative and structural.")
    requestedOutputsRatios: bool = Field("", title="Statement 7", description="You stated that your requested outputs include odds ratios, risk ratios or other proportionate risks. Please confirm the underlying contingency table has been produced and is included in the requested outputs.")
    requestedOutputsHazard: bool = Field("", title="Statement 8", description="You stated that your requested outputs include hazard or survival tables. Please confirm the following.")
    numberPatientsSurvived: bool = Field("", title="Statement 9", description="The number of patients who survived is ≥5.")
    exitDatesRelatives: bool = Field("", title="Statement 10", description="Exit dates are relative, not absolute.")
    noDatesWithSingleExit: bool = Field("", title="Statement 11", description="There are no dates with a single exit.")

class AirlockRequest(AzureTREModel):
    """
    Airlock request
    """
    id: str = Field(title="Id", description="GUID identifying the resource")
    resourceVersion: int = 0
    createdBy: dict = {}
    createdWhen: float = Field(None, title="Creation time of the request")
    updatedBy: dict = {}
    updatedWhen: float = 0
    history: List[AirlockRequestHistoryItem] = []
    workspaceId: str = Field("", title="Workspace ID", description="Service target Workspace id")
    type: AirlockRequestType = Field("", title="Airlock request type")
    files: List[AirlockFile] = Field([], title="Files of the request")
    title: str = Field("Airlock Request", title="Brief title for the request")
    businessJustification: str = Field("Business Justification", title="Explanation that will be provided to the request reviewer")
    status = AirlockRequestStatus.Draft
    statusMessage: Optional[str] = Field(title="Optional - contains additional information about the current status.")
    reviews: Optional[List[AirlockReview]]
    etag: Optional[str] = Field(title="_etag", alias="_etag")
    reviewUserResources: Dict[str, AirlockReviewUserResource] = Field({}, title="User resources created for Airlock Reviews")
    triageStatements: Optional[List[AirlockRequestTriageStatements]] = Field("Triage Statements for Airlock Export requests", title="User given statements for acceptance.")
    contactTeamForm: Optional[List[AirlockRequestContactTeamForm]] = Field("Contact Team Form for Airlock Export requests", title="User given information regarding Airlock Export requests.")
    unsafeStatistics: Optional[List[AirlockRequestUnsafeStatisticsStatements]] = Field("Specific details about unsafe provided statistics", title="Specific user given details about unsafe provided statistics.")
    otherStatistics: Optional[List[AirlockRequestOtherStatisticsStatements]] = Field("Specific details about unsafe provided statistics", title="Specific user given details about unsafe provided statistics.")

    # SQL API CosmosDB saves ETag as an escaped string: https://github.com/microsoft/AzureTRE/issues/1931
    @validator("etag", pre=True)
    def parse_etag_to_remove_escaped_quotes(cls, value):
        if value:
            return value.replace('\"', '')
