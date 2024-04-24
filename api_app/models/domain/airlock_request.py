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
    patientLevelData: bool = Field("", title="Statement 2", description="No event or patient level data are included in the requested outputs.")
    requestedOutputsClear: bool = Field("", title="Statement 3", description="All requested outputs are sufficiently clear and comprehensible to permit output checking without the need for dataset- or project-specific knowledge.")
    requestedOutputsStatic: bool = Field("", title="Statement 4", description="All requested outputs are static.")
    requestedOutputsPermittedFiles: bool = Field("", title="Statement 5", description="All requested outputs use permitted file types.")
    hiddenInformation: bool = Field("", title="Statement 6", description="No hidden information has been included (e.g., embedded files), comments, track changes).")


class AirlockRequestContactTeamForm(AzureTREModel):
    """
    MHRA's specific fields for sending messages to Contact Team
    """
    requiredDisclosureAlignment: str = Field("Question 1", title="Why are outputs required that do not align with the disclosure control rules?")
    measuresTakenMinimiseDisclosure: str = Field("Question 2", title="What measures have been taken to minimise the risk of potentially disclosive outputs?")
    transferToThirdParty: str = Field("Question 3", title="Will the outputs be transferred to any other third party?")


class AirlockRequestStatisticsStatements(AzureTREModel):
    """
    MHRA's specific statistics user statements for Export requests
    """
    codeLists: bool = Field("", title="Statement 1", description="Code lists or programming code")
    statisticalTests: bool = Field("", title="Statement 2", description="Statistical hypothesis tests (e.g., t-test, chi-square, R-square, standard errors)")
    statisticalTestsConfirmation: bool = Field("", title="Statement 3", description="You stated that your requested outputs include statistical hypothesis tests")
    coefficientsAssociation: bool = Field("", title="Statement 4", description="Coefficients of association (e.g., estimated coefficients, models, AN(C)OVA, correlation tables, density plots, kernel density plots)")
    coefficientsAssociationResidualDegrees: bool = Field("", title="Statement 5", description="The residual degrees of freedom (number of observations less number of variables) exceeds five")
    coefficientsAssociationModelNotSaturated: bool = Field("", title="Statement 6", description="The model is not saturated (i.e., not all variables are categorical and fully interacted)")
    coefficientsAssociationRegressionNotIncluded: bool = Field("", title="Statement 7", description="Your outputs do not include a regression with a single binary explanatory variable")
    shape: bool = Field("", title="Statement 8", description="Shape (e.g., standard deviation, skewness, kurtosis)")
    shapeStandardDeviations: bool = Field("", title="Statement 9", description="Any standard deviations are greater than zero")
    shapeMinFive: bool = Field("", title="Statement 10", description="All statistics of shape were calculated for a minimum of five patients or GP practices")
    mode: bool = Field("", title="Statement 11", description="Mode")
    modeConfirmation: bool = Field("", title="Statement 12", description="You stated that your requested outputs include modes")
    ratios: bool = Field("", title="Statement 13", description="Non-linear concentration ratios (e.g., Herfindahl-Hirchsmann index, diversity index)")
    ratiosConfirmationNRatios: bool = Field("", title="Statement 14", description="N>2")
    ratiosConfirmationHRatios: bool = Field("", title="Statement 15", description="H<0.81")
    giniCoefficients: bool = Field("", title="Statement 16", description="Gini coefficients or Lorenz curves")
    giniCoefficientsConfirmationN: bool = Field("", title="Statement 17", description="N>2")
    giniCoefficientsConfirmationLessThan: bool = Field("", title="Statement 18", description="The coefficient is less than 100%")
    frequencies: bool = Field("", title="Statement 19", description="Frequencies (e.g. frequency tables, histograms, shares, alluvial flow graphs, heat maps, line graphs, pie charts, scatter graphs, scatter plots, smoothed histograms, waterfall charts)")
    frequenciesSmallFrequenciesSuppressed: bool = Field("", title="Statement 20", description="All counts <5 and frequencies derived from groups containing <5 patients or GP practices have been suppressed.")
    frequenciesZerosFullCells: bool = Field("", title="Statement 21", description="All zeroes and full cells (100%) are evidential or structural (i.e., something you would expect).")
    frequenciesUnderlyingValuesIndependent: bool = Field("", title="Statement 22", description="Underlying values are genuinely independent (i.e., they do not come from the same patient, the patients do not all have the same family number and do not all come from the same GP practice).")
    frequenciesCategoriesComprehensiveData: bool = Field("", title="Statement 23", description="The categories are comprehensive and apply to all data (i.e., all categories of each categorical variable are presented).")
    position: bool = Field("", title="Statement 24", description="Position (e.g., median, percentiles, box plots)")
    positionConfirmation: bool = Field("", title="Statement 25", description="You stated that your requested outputs include statistics of position. Please confirm the numbers for each group (and complementary groups) are ≥5.")
    extremeValues: bool = Field("", title="Statement 26", description="Extreme values (e.g., maxima, minima)")
    extremeValuesConfirmation: bool = Field("", title="Statement 27", description="You stated that your requested outputs include extreme values. Please confirm the maximum or minimum presented are non-informative and structural.")
    linearAggregates: bool = Field("", title="Statement 28", description="Linear aggregates (e.g., means, totals, simple indexes, linear correlation ratios, bar graphs, mean plots)")
    linearAggregatesDerivedGroups: bool = Field("", title="Statement 29", description="The linear aggregates have been derived from groups containing ≥5 patients or GP practices.")
    linearAggregatesPRatioDominanceRule: bool = Field("", title="Statement 30", description="The P-ratio dominance rule has been calculated and is greater than 10%. (NB: ACRO will check this automatically).")
    linearAggregatesNKDominanceRule: bool = Field("", title="Statement 31", description="The N-K dominance rule has been calculated for the 2 largest values and is less than 90%. (NB: ACRO will check this automatically).")
    oddsRatios: bool = Field("", title="Statement 32", description="Odds ratios, risk ratios or other proportionate risks")
    oddsRatiosConfirmation: bool = Field("", title="Statement 33", description="You stated that your requested outputs include odds ratios, risk ratios or other proportionate risks. Please confirm the underlying contingency table has been produced and is included in the requested outputs.")
    hazardSurvivalTables: bool = Field("", title="Statement 34", description="Hazard and survival tables (e.g., tables of survival/death rates, Kaplan-Meier graphs)")
    hazardSurvivalTablesNumberPatientsSurvived: bool = Field("", title="Statement 35", description="The number of patients who survived is ≥5.")
    hazardSurvivalTablesExitDatesRelatives: bool = Field("", title="Statement 36", description="Exit dates are relative, not absolute.")
    hazardSurvivalTablesNoDatesWithSingleExit: bool = Field("", title="Statement 37", description="There are no dates with a single exit.")
    isAcroUsed: bool = Field("", title="Statement 38", description="Is Acro used")
    other: bool = Field("", title="Statement 39", description="Other")


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
    triageLevel: Optional[str] = Field("Triage Level assigned to Airlock Export requests", title="Triage Level assigned to Airlock Export requests.")
    triageStatements: Optional[List[AirlockRequestTriageStatements]] = Field("Triage Statements for Airlock Export requests", title="User given statements for acceptance.")
    contactTeamForm: Optional[List[AirlockRequestContactTeamForm]] = Field("Contact Team Form for Airlock Export requests", title="User given information regarding Airlock Export requests.")
    statisticsLevel: Optional[str] = Field("Statistics Level assigned to Airlock Export requests", title="Statistics Level assigned to Airlock Export requests.")
    statisticsStatements: Optional[List[AirlockRequestStatisticsStatements]] = Field("Statistics Statements for Airlock Export requests", title="User given statements for acceptance.")

    # SQL API CosmosDB saves ETag as an escaped string: https://github.com/microsoft/AzureTRE/issues/1931
    @validator("etag", pre=True)
    def parse_etag_to_remove_escaped_quotes(cls, value):
        if value:
            return value.replace('\"', '')
