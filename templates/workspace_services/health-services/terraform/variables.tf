variable "workspace_id" {
  type        = string
  description = "TRE workspace ID"
}

variable "aad_authority_url" {
  type        = string
  description = "Active directory"
}

variable "tre_id" {
  type        = string
  description = "TRE ID"
}

variable "tre_resource_id" {
  type        = string
  description = "Resource ID"
}

variable "deploy_fhir" {
  type        = bool
  description = "Indicates if FHIR should be created in the Azure Health Data Services Workspace."
}

variable "fhir_kind" {
  type        = string
  description = "FHIR version that will be deployed."
}

variable "deploy_dicom" {
  type        = bool
  description = "Indicates if DICOM should be created in the Azure Health Data Services Workspace."
}

variable "workspace_owners_group_id" {
  type        = string
  description = "Object ID of the workspace owners AAD group"

  validation {
    condition     = length(trimspace(var.workspace_owners_group_id)) > 0
    error_message = "workspace_owners_group_id must be provided; Entra ID workspace groups are required."
  }
}

variable "workspace_researchers_group_id" {
  type        = string
  description = "Object ID of the workspace researchers AAD group"

  validation {
    condition     = length(trimspace(var.workspace_researchers_group_id)) > 0
    error_message = "workspace_researchers_group_id must be provided; Entra ID workspace groups are required."
  }
}

variable "arm_environment" {
  type = string
}
