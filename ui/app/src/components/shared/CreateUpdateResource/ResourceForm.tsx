import { MessageBar, MessageBarType, Spinner, SpinnerSize } from "@fluentui/react";
import { useEffect, useState } from "react";
import { LoadingState } from "../../../models/loadingState";
import { HttpMethod, useAuthApiCall } from "../../../useAuthApiCall";
import Form from "@rjsf/fluent-ui";

interface ResourceFormProps {
    templatePath: string,
    createResource: (resource: {}) => void
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
                console.log(templateResponse);
                setTemplate(templateResponse);
                setLoading(LoadingState.Ok);
            } catch {
                setLoading(LoadingState.Error);
            }
        };

        // Fetch full resource template only if not in state
        if (!template) {
            getFullTemplate();
        }
    });

    switch (loading) {
        case LoadingState.Ok:
            return (
                template ? <div style={{ marginTop: 20 }}>
                    <Form schema={template} onSubmit={(e: any) => props.createResource(e.formData)}/>
                </div> : null
            )
        case LoadingState.Error:
            return (
                <MessageBar
                    messageBarType={MessageBarType.error}
                    isMultiline={true}
                >
                    <h3>Error retrieving template</h3>
                    <p>There was an error retrieving the full resource template. Please see the browser console for details.</p>
                </MessageBar>
            );
        default:
            return (
                <div style={{ marginTop: 20 }}>
                    <Spinner label="Loading template" ariaLive="assertive" labelPosition="top" size={SpinnerSize.large} />
                </div>
            )
    }
}