// Convention: any resource property whose name contains this token holds a
// reference (Key Vault secret identifier) to a secret in the workspace Key Vault,
// rather than the secret value itself.
export const KEYVAULT_SECRET_ID_TOKEN = "keyvault_secret_id";

export const isSecretProperty = (propertyName: string): boolean => propertyName.includes(KEYVAULT_SECRET_ID_TOKEN);

export interface Secret {
  key: string;
  value: string;
}
