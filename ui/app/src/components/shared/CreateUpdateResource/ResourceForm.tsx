import { DefaultButton, MessageBar, MessageBarType, Spinner, SpinnerSize } from "@fluentui/react";
import { useEffect, useState } from "react";
import { LoadingState } from "../../../models/loadingState";
import { HttpMethod, useAuthApiCall } from "../../../useAuthApiCall";

interface ResourceFormProps {
    templatePath: string,
    onCreateResource: () => void
}

export const ResourceForm: React.FunctionComponent<ResourceFormProps> = (props: ResourceFormProps) => {
    const [template, setTemplate] = useState<any | null>(null);
    const [loading, setLoading] = useState(LoadingState.Loading as LoadingState);
    const apiCall = useAuthApiCall();

    useEffect(() => {
        const getFullTemplate = async () => {
            try {
                // Get the full resource template containing the required parameters
                const templateResponse = await apiCall(props.templatePath, HttpMethod.Get);
                setTemplate(templateResponse.template);
                setLoading(LoadingState.Ok);
            } catch {
                setLoading(LoadingState.Error);
            }
        };

        // Fetch resource templates only if not already fetched
        getFullTemplate();
    });

    switch (loading) {
        case LoadingState.Ok:
            return (
                template ? <p>{template.name}</p> : null
            )
        case LoadingState.Error:
            return (
                <MessageBar
                    messageBarType={MessageBarType.error}
                    isMultiline={true}
                >
                    <h3>Error retrieving template</h3>
                    <p>There was an error retrieving the template. Please see the browser console for details.</p>
                </MessageBar>
            );
        default:
            return (
                <div style={{ marginTop: '20px' }}>
                    <Spinner label="Loading template" ariaLive="assertive" labelPosition="top" size={SpinnerSize.large} />
                </div>
            )
    }
}