variable "arm_environment" {
  type = string

  validation {
    condition     = contains(["public", "usgovernment"], var.arm_environment)
    error_message = "Allowed values for input_parameter are \"public\" or \"usgovernment\"."
  }

}
