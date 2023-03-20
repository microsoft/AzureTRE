output "private_links" {
  value = lookup(local.private_links, var.arm_environment, null)
}

output "suffixes" {
  value = lookup(local.suffixes, var.arm_environment, null)
}
