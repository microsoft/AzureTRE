# The client_id of the per-workspace airlock SAS signer app registration.
# Empty when register_aad_application is false (signing falls back to the shared API identity).
# Persisted as a workspace property and read by the API/airlock processor when minting SAS.
output "airlock_signer_client_id" {
  value = var.register_aad_application ? azuread_application.airlock_signer[0].client_id : ""
}
