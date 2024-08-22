import uuid
from datetime import datetime
from typing import List
from pydantic import BaseModel, Field
from models.domain.operation import Operation
from models.schemas.operation import get_sample_operation
from models.domain.airlock_request import AirlockActions, AirlockRequest, AirlockRequestType


def get_sample_airlock_review(airlock_review_id: str) -> dict:
    return {
        "reviewId": airlock_review_id,
        "reviewDecision": "Describe why the request was approved/rejected",
        "decisionExplanation": "Describe why the request was approved/rejected"
    }


def get_sample_airlock_request(workspace_id: str, airlock_request_id: str) -> dict:
    return {
        "requestId": airlock_request_id,
        "workspaceId": workspace_id,
        "status": "draft",
        "type": "import",
        "files": [],
        "title": "a request title",
        "businessJustification": "some business justification",
        "createdBy": {
            "id": "a user id",
            "name": "a user name"
        },
        "createdWhen": datetime.utcnow().timestamp(),
        "reviews": [
            get_sample_airlock_review("29990431-5451-40e7-a58a-02e2b7c3d7c8"),
            get_sample_airlock_review("02dc0f29-351a-43ec-87e7-3dd2b5177b7f")]
    }


def get_sample_airlock_request_with_allowed_user_actions(workspace_id: str) -> dict:
    return {
        "airlockRequest": get_sample_airlock_request(workspace_id, str(uuid.uuid4())),
        "allowedUserActions": [AirlockActions.Cancel, AirlockActions.Review, AirlockActions.Submit],
    }


class AirlockRequestInResponse(BaseModel):
    airlockRequest: AirlockRequest

    class Config:
        schema_extra = {
            "example": {
                "airlockRequest": get_sample_airlock_request("933ad738-7265-4b5f-9eae-a1a62928772e", "121e921f-a4aa-44b3-90a9-e8da030495ef")
            }
        }


class AirlockRequestAndOperationInResponse(BaseModel):
    airlockRequest: AirlockRequest
    operation: Operation

    class Config:
        schema_extra = {
            "example": {
                "airlockRequest": get_sample_airlock_request("933ad738-7265-4b5f-9eae-a1a62928772e", "121e921f-a4aa-44b3-90a9-e8da030495ef"),
                "operation": get_sample_operation("121e921f-a4aa-44b3-90a9-e8da030495ef")
            }
        }


class AirlockRequestWithAllowedUserActions(BaseModel):
    airlockRequest: AirlockRequest = Field([], title="Airlock Request")
    allowedUserActions: List[str] = Field([], title="actions that the requesting user can do on the request")

    class Config:
        schema_extra = {
            "example": get_sample_airlock_request_with_allowed_user_actions("933ad738-7265-4b5f-9eae-a1a62928772e"),
        }


class AirlockRequestWithAllowedUserActionsInList(BaseModel):
    airlockRequests: List[AirlockRequestWithAllowedUserActions] = Field([], title="Airlock Requests")

    class Config:
        schema_extra = {
            "example": {
                "airlockRequests": [
                    get_sample_airlock_request_with_allowed_user_actions("933ad738-7265-4b5f-9eae-a1a62928772e"),
                    get_sample_airlock_request_with_allowed_user_actions("933ad738-7265-4b5f-9eae-a1a62928772e")
                ]
            }
        }


class AirlockRequestInCreate(BaseModel):
    type: AirlockRequestType = Field("", title="Airlock request type", description="Specifies if this is an import or an export request")
    title: str = Field("Airlock Request", title="Brief title for the request")
    businessJustification: str = Field("Business Justifications", title="Explanation that will be provided to the request reviewer")
    isEUUAAccepted: bool = Field("User Agreement Acceptance", title="Mark if the User Agreement was accepted")
    properties: dict = Field({}, title="Airlock request parameters", description="Values for the parameters required by the Airlock request specification")

    class Config:
        schema_extra = {
            "example": {
                "type": "import",
                "title": "a request title",
                "businessJustification": "some business justification",
                "isEUUAAccepted": "true"
            }
        }


class AirlockReviewInCreate(BaseModel):
    approval: bool = Field("", title="Airlock review decision", description="Airlock review decision")
    decisionExplanation: str = Field("Decision Explanation", title="Explanation of the reviewer for the reviews decision")

    class Config:
        schema_extra = {
            "example": {
                "approval": "True",
                "decisionExplanation": "the reason why this request was approved/rejected"
            }
        }


class AirlockRequestTriageStatements(BaseModel):
    rdgConsistent: bool = Field("", title="Statement 1", description="Requested outputs are consistent with the RDG approved protocol associated with this workspace.")
    patientLevelData: bool = Field("", title="Statement 2", description="No event or patient level data are included in the requested outputs.")
    requestedOutputsClear: bool = Field("", title="Statement 3", description="All requested outputs are sufficiently clear and comprehensible to permit output checking without the need for dataset- or project-specific knowledge.")
    requestedOutputsStatic: bool = Field("", title="Statement 4", description="All requested outputs are static.")
    requestedOutputsPermittedFiles: bool = Field("", title="Statement 5", description="All requested outputs use permitted file types.")
    hiddenInformation: bool = Field("", title="Statement 6", description="No hidden information has been included (e.g., embedded files), comments, track changes).")

    class Config:
        schema_extra = {
            "example": {
                "rdgConsistent": "True",
                "patientLevelData": "False",
                "requestedOutputsClear": "True",
                "requestedOutputsStatic": "True",
                "requestedOutputsPermittedFiles": "True",
                "hiddenInformation": "False"
            }
        }


class AirlockRequestContactTeamForm(BaseModel):
    requiredDisclosureAlignment: str = Field("Question 1", title="Why are outputs required that do not align with the disclosure control rules?")
    measuresTakenMinimiseDisclosure: str = Field("Question 2", title="What measures have been taken to minimise the risk of potentially disclosive outputs?")
    transferToThirdParty: str = Field("Question 3", title="Will the outputs be transferred to any other third party?")

    class Config:
        schema_extra = {
            "example": {
                "requiredDisclosureAlignment": "I need this output because it'll be used in a very important publication.",
                "measuresTakenMinimiseDisclosure": "I took measures 1, 2, 3, 4, etc. for minimising diclosure information.",
                "transferToThirdParty": "The output generated will not be transferred to thrid parties."
            }
        }


class AirlockRequestStatisticsStatements(BaseModel):
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
    isAcroUsedPosition: bool = Field("", title="Statement 38", description="Is Acro used for Position")
    isAcroUsedLinearAggregates: bool = Field("", title="Statement 39", description="Is Acro used for Linear Aggregates")
    other: bool = Field("", title="Statement 40", description="Other")

    class Config:
        schema_extra = {
            "example": {
                "codeLists": "False",
                "statisticalTests": "False",
                "statisticalTestsConfirmation": "False",
                "coefficientsAssociation": "False",
                "coefficientsAssociationResidualDegrees": "False",
                "coefficientsAssociationModelNotSaturated": "False",
                "coefficientsAssociationRegressionNotIncluded": "False",
                "shape": "False",
                "shapeStandardDeviations": "False",
                "shapeMinFive": "False",
                "mode": "False",
                "modeConfirmation": "False",
                "ratios": "False",
                "ratiosConfirmationNRatios": "False",
                "ratiosConfirmationHRatios": "False",
                "giniCoefficients": "False",
                "giniCoefficientsConfirmationN": "False",
                "giniCoefficientsConfirmationLessThan": "False",
                "frequencies": "False",
                "frequenciesSmallFrequenciesSuppressed": "False",
                "frequenciesZerosFullCells": "False",
                "frequenciesUnderlyingValuesIndependent": "False",
                "frequenciesCategoriesComprehensiveData": "False",
                "position": "False",
                "positionConfirmation": "False",
                "extremeValues": "False",
                "extremeValuesConfirmation": "False",
                "linearAggregates": "False",
                "linearAggregatesDerivedGroups": "False",
                "linearAggregatesPRatioDominanceRule": "False",
                "linearAggregatesNKDominanceRule": "False",
                "oddsRatios": "False",
                "oddsRatiosConfirmation": "False",
                "hazardSurvivalTables": "False",
                "hazardSurvivalTablesNumberPatientsSurvived": "False",
                "hazardSurvivalTablesExitDatesRelatives": "False",
                "hazardSurvivalTablesNoDatesWithSingleExit": "False",
                "isAcroUsedPosition": "False",
                "isAcroUsedLinearAggregates": "False",
                "other": "False"
            }
        }
