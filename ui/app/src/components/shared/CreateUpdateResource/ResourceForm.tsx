import { MessageBar, MessageBarType, Spinner, SpinnerSize } from "@fluentui/react";
import { useContext, useEffect, useState } from "react";
import { LoadingState } from "../../../models/loadingState";
import { HttpMethod, ResultType, useAuthApiCall } from "../../../useAuthApiCall";
import Form from "@rjsf/fluent-ui";
import { Operation } from "../../../models/operation";
import { WorkspaceContext } from "../../../contexts/WorkspaceContext";

interface ResourceFormProps {
    templateName: string,
    templatePath: string,
    resourcePath: string,
    onCreateResource: (operation: Operation) => void
}

export const ResourceForm: React.FunctionComponent<ResourceFormProps> = (props: ResourceFormProps) => {
    const [template, setTemplate] = useState<any | null>(null);
    const [loading, setLoading] = useState(LoadingState.Loading as LoadingState);
    const [deployError, setDeployError] = useState(false);
    const apiCall = useAuthApiCall();
    const workspaceCtx = useContext(WorkspaceContext);

    useEffect(() => {
        const getFullTemplate = async () => {
            try {
                // Get the full resource template containing the required parameters
                const templateResponse = await apiCall(props.templatePath, HttpMethod.Get);
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
    }, [apiCall, props.templatePath, template]);

    const createResource = async (formData: {}) => {
        setDeployError(false);
        const resource = { templateName: props.templateName, properties: formData };
        console.log(resource);
        const response = await apiCall(props.resourcePath, HttpMethod.Post, workspaceCtx.workspaceClientId, resource, ResultType.JSON);
        if (response) {
            props.onCreateResource(response.operation);
        } else {
            setDeployError(true);
        }
    }

    switch (loading) {
        case LoadingState.Ok:
            return (
                template ? <div style={{ marginTop: 20 }}>
                    <Form schema={template} onSubmit={(e: any) => createResource(e.formData)}/>
                    { 
                        deployError ? <MessageBar messageBarType={MessageBarType.error}>
                            <p>The API returned an error. Check the console for details or retry.</p>
                        </MessageBar> : null 
                    }
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
