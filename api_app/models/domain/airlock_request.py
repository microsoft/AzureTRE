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
    rdgConsistent: bool = Field(title="Statement 1", description="Requested outputs are consistent with the RDG approved protocol associated with this workspace.")
    noPatientLevelData: bool = Field(title="Statement 2", description="No event or patient level data are included in the requested outputs.")
    requestedOutputsClear: bool = Field(title="Statement 3", description="All requested outputs are sufficiently clear and comprehensible to permit output checking without the need for dataset- or project-specific knowledge.")
    requestedOutputsStatic: bool = Field(title="Statement 4", description="All requested outputs are static.")
    requestedOutputsPermittedFiles: bool = Field(title="Statement 5", description="All requested outputs use permitted file types.")
    noHiddenInformation: bool = Field(title="Statement 6", description="No hidden information has been included (e.g., embedded files), comments, track changes).")


class AirlockRequestStatisticsStatements(AzureTREModel):
    """
    MHRA's specific statistics user statements for Export requests
    """
    codeLists: bool = Field(title="Statement 1", description="Code lists or programming code")
    safeStatistics: bool = Field(title="Statement 2", description="Safe statistics")
    statisticalTests: bool = Field(title="Statement 3", description="Statistical hypothesis tests (e.g., t-test, chi-square, R-square, standard errors)")
    coefficientsAssociation: bool = Field(title="Statement 4", description="Coefficients of association (e.g., estimated coefficients, models, AN(C)OVA, correlation tables, density plots, kernel density plots)")
    shape: bool = Field(title="Statement 5", description="Shape (e.g., standard deviation, skewness, kurtosis)")
    mode: bool = Field(title="Statement 6", description="Mode")
    ratios: bool = Field(title="Statement 7", description="Non-linear concentration ratios (e.g., Herfindahl-Hirchsmann index, diversity index)")
    giniCoefficients: bool = Field(title="Statement 8", description="Gini coefficients or Lorenz curves")
    unsafeStatistics: bool = Field(title="Statement 9", description="Unsafe statistics")
    frequencies: bool = Field(title="Statement 10", description="Frequencies (e.g. frequency tables, histograms, shares, alluvial flow graphs, heat maps, line graphs, pie charts, scatter graphs, scatter plots, smoothed histograms, waterfall charts)")
    position: bool = Field(title="Statement 11", description="Position (e.g., median, percentiles, box plots)")
    extremeValues: bool = Field(title="Statement 12", description="Extreme values (e.g., maxima, minima)")
    linearAggregates: bool = Field(title="Statement 13", description="Linear aggregates (e.g., means, totals, simple indexes, linear correlation ratios, bar graphs, mean plots)")
    riskRatios: bool = Field(title="Statement 14", description="Odds ratios, risk ratios or other proportionate risks")
    survivalTables: bool = Field(title="Statement 15", description="Hazard and survival tables (e.g., tables of survival/death rates, Kaplan-Meier graphs)")
    other: bool = Field(title="Statement 16", description="Other")


class AirlockRequestSafeStatisticsStatements(AzureTREModel):
    """
    MHRA's safe specific statistics user statements for Export requests
    """
    testConfirmation: bool = Field(title="Statement 1", description="You stated that your requested outputs include statistical hypothesis tests")
    coefficientsConfirmation: bool = Field(title="Statement 2", description="You stated that your requested outputs include coefficients of association")
    residualDegrees: bool = Field(title="Statement 3", description="The residual degrees of freedom (number of observations less number of variables) exceeds five")
    modelNotSaturated: bool = Field(title="Statement 4", description="The model is not saturated (i.e., not all variables are categorical and fully interacted)")
    regressionNotIncluded: bool = Field(title="Statement 5", description="Your outputs do not include a regression with a single binary explanatory variable")
    shapeConfirmation: bool = Field(title="Statement 6", description="You stated that your requested outputs include statistics of shape")
    standardDeviations: bool = Field(title="Statement 7", description="Any standard deviations are greater than zero")
    shapeMinFive: bool = Field(title="Statement 8", description="All statistics of shape were calculated for a minimum of five patients or GP practices")
    modeConfirmation: bool = Field(title="Statement 9", description="You stated that your requested outputs include modes")
    ratiosConfirmation: bool = Field(title="Statement 10", description="You stated that your requested outputs include non-linear concentration ratios")
    nRatio: bool = Field(title="Statement 11", description="N>2")
    hRatio: bool = Field(title="Statement 12", description="H<0.81")
    giniCoefficientsConfirmation: bool = Field(title="Statement 13", description="You stated that your requested outputs include Gini coefficients or Lorenz curves")
    nGiniCoefficient: bool = Field(title="Statement 14", description="N>2")
    coefficientLessThan: bool = Field(title="Statement 15", description="The coefficient is less than 100%")


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
    triageStatements: List[AirlockRequestTriageStatements] = Field("Triage Statements for Airlock Export requests", title="User given statements for acceptance.")
    statisticsStatements: List[AirlockRequestStatisticsStatements] = Field("Statistics Statements for Airlock Export requests", title="User given statements for acceptance.")
    safeStatisticsStatements: List[AirlockRequestSafeStatisticsStatements] = Field("Safe Statistics Statements for Airlock Export requests", title="User given statements for acceptance.")

    # SQL API CosmosDB saves ETag as an escaped string: https://github.com/microsoft/AzureTRE/issues/1931
    @validator("etag", pre=True)
    def parse_etag_to_remove_escaped_quotes(cls, value):
        if value:
            return value.replace('\"', '')
