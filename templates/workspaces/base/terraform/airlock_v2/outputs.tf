# The client_id of the per-workspace airlock SAS signer app registration.
# Persisted as a workspace property and read by the API/airlock processor when minting SAS.
output "airlock_signer_client_id" {
  value = azuread_application.airlock_signer.client_id
}
