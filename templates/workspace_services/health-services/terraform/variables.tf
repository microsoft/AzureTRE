variable "workspace_id" {
  type        = string
  description = "TRE workspace ID"
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

