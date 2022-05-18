import { DefaultButton, MessageBar, MessageBarType, Spinner, SpinnerSize, Stack } from "@fluentui/react";
import { useEffect, useState } from "react";
import { ApiEndpoint } from "../../../models/apiEndpoints";
import { LoadingState } from "../../../models/loadingState";
import { ResourceType } from "../../../models/resourceType";
import { HttpMethod, useAuthApiCall } from "../../../useAuthApiCall";

interface SelectTemplateProps {
    resourceType: ResourceType,
    serviceName?: string,
    onSelectTemplate: (templateName: string) => void
}

const getTemplatePath = (resourceType: string, serviceName?: string) => {
    switch (resourceType) {
        case ResourceType.Workspace:
            return ApiEndpoint.WorkspaceTemplates;
        case ResourceType.WorkspaceService:
            return ApiEndpoint.WorkspaceServiceTemplates;
        case ResourceType.UserResource:
            if (serviceName) {
                return `${ApiEndpoint.WorkspaceServiceTemplates}/${serviceName}/${ApiEndpoint.UserResourceTemplates}`;
            } else {
                throw Error('serviceTemplateName must also be passed for workspace-service resourceType.');
            }
        default:
            throw Error('Unsupported resource type.');
    }
}

export const SelectTemplate: React.FunctionComponent<SelectTemplateProps> = (props: SelectTemplateProps) => {
    const [templates, setTemplates] = useState<any[] | null>(null);
    const [loading, setLoading] = useState(LoadingState.Loading as LoadingState);
    const apiCall = useAuthApiCall();

    useEffect(() => {
        const getTemplates = async () => {
            try {
                // Construct the templates API path for specified ResourceType
                const path = getTemplatePath(props.resourceType, props.serviceName);

                // Get the templates from the API
                const templatesResponse = await apiCall(path, HttpMethod.Get);
                setTemplates(templatesResponse.templates);
                setLoading(LoadingState.Ok);
            } catch {
                setLoading(LoadingState.Error);
            }
        };

        // Fetch resource templates only if not already fetched
        if (!templates) {
            getTemplates();
        }
    });

    switch (loading) {
        case LoadingState.Ok:
            return (
                templates ? <Stack>
                {
                    templates.map((template: any, i) => {
                        return (
                        <div key={i}>
                            <h2>{template.title}</h2>
                            <p>{template.description}</p>
                            <DefaultButton text="Create" onClick={() => props.onSelectTemplate(template.name)}/>
                        </div>
                        )
                    })
                }
                </Stack> : null
            )
        case LoadingState.Error:
            return (
                <MessageBar
                    messageBarType={MessageBarType.error}
                    isMultiline={true}
                >
                    <h3>Error retrieving templates</h3>
                    <p>There was an error retrieving templates. Please see the browser console for details.</p>
                </MessageBar>
            );
        default:
            return (
                <div style={{ marginTop: '20px' }}>
                    <Spinner label="Loading templates" ariaLive="assertive" labelPosition="top" size={SpinnerSize.large} />
                </div>
            )
    }
}