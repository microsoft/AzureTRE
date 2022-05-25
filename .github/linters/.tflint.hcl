config {
  module = true
  force = false
}

# https://github.com/github/super-linter/issues/2954
plugin "aws" {
  enabled = false  # Override: disable AWS
}

plugin "azurerm" {
    enabled = true
}
