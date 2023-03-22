output "private_links" {
  value = local.private_links[var.arm_environment]
}

output "suffixes" {
  value = local.suffixes[var.arm_environment]
}
