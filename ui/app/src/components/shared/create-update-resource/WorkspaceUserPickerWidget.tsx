import { useCallback, useEffect, useState } from "react";
import { ComboBox, IComboBox, IComboBoxOption, MessageBar, MessageBarType } from "@fluentui/react";
import { WidgetProps } from "@rjsf/utils";
import { useAccount, useMsal } from "@azure/msal-react";
import { HttpMethod, useAuthApiCall } from "../../../hooks/useAuthApiCall";
import { ApiEndpoint } from "../../../models/apiEndpoints";

interface WorkspaceUser {
  id: string;
  displayName: string;
  userPrincipalName: string;
}

export const WorkspaceUserPickerWidget: React.FunctionComponent<WidgetProps> = (props) => {
  const { id, value, required, disabled, readonly, onChange, label } = props;
  const workspaceId = props.formContext?.workspaceId;
  const workspaceApplicationIdURI = props.formContext?.workspaceApplicationIdURI;
  const apiCall = useAuthApiCall();
  const { accounts } = useMsal();
  const currentAccount = useAccount(accounts[0] || {});
  const [options, setOptions] = useState<IComboBoxOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    const getWorkspaceUsers = async () => {
      try {
        const response = await apiCall(
          `${ApiEndpoint.Workspaces}/${workspaceId}/${ApiEndpoint.Users}`,
          HttpMethod.Get,
          workspaceApplicationIdURI,
        );
        const users = response.users as WorkspaceUser[];
        const currentUserId = currentAccount?.localAccountId.split(".")[0];
        setOptions(
          users
            .filter((user) => user.id !== currentUserId)
            .map((user) => ({
              key: user.id,
              text: `${user.displayName} (${user.userPrincipalName})`,
            })),
        );
      } catch (err: any) {
        setErrorMessage("Unable to load the list of workspace users.");
      } finally {
        setLoading(false);
      }
    };

    if (workspaceId) getWorkspaceUsers();
  }, [apiCall, workspaceId, workspaceApplicationIdURI, currentAccount?.localAccountId]);

  const handleChange = useCallback(
    (_event: React.FormEvent<IComboBox>, option?: IComboBoxOption) => {
      onChange(option ? (option.key as string) : undefined);
    },
    [onChange],
  );

  if (errorMessage) {
    return <MessageBar messageBarType={MessageBarType.error}>{errorMessage}</MessageBar>;
  }

  const noUsersFound = !loading && options.length === 0;

  let placeholder = "Select a user";
  if (loading) placeholder = "Loading workspace users...";
  else if (noUsersFound) placeholder = "No other workspace users found";

  return (
    <ComboBox
      id={id}
      label={label}
      required={required}
      disabled={disabled || readonly || noUsersFound}
      allowFreeform={false}
      autoComplete="on"
      selectedKey={value || null}
      options={options}
      placeholder={placeholder}
      onChange={handleChange}
    />
  );
};
