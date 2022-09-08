import { DefaultButton, MessageBar, MessageBarType, Spinner, SpinnerSize, Stack } from "@fluentui/react";
import { useEffect, useState } from "react";
import { LoadingState } from "../../../models/loadingState";
import { HttpMethod, useAuthApiCall } from "../../../hooks/useAuthApiCall";
import { APIError } from "../../../models/exceptions";
import { ExceptionLayout } from "../ExceptionLayout";

interface SelectTemplateProps {
    templatesPath: string,
    onSelectTemplate: (templateName: string) => void
}

export const SelectTemplate: React.FunctionComponent<SelectTemplateProps> = (props: SelectTemplateProps) => {
    const [templates, setTemplates] = useState<any[] | null>(null);
    const [loading, setLoading] = useState(LoadingState.Loading as LoadingState);
    const apiCall = useAuthApiCall();
    const [apiError, setApiError] = useState({} as APIError);

    useEffect(() => {
        const getTemplates = async () => {
            try {
                // Get the templates from the API
                const templatesResponse = await apiCall(props.templatesPath, HttpMethod.Get);
                setTemplates(templatesResponse.templates);
                setLoading(LoadingState.Ok);
            } catch (err: any){
                err.userMessage = 'Error retrieving templates';
                setApiError(err);
                setLoading(LoadingState.Error);
            }
        };

        // Fetch resource templates only if not already fetched
        if (!templates) {
            getTemplates();
        }
    }, [apiCall, props.templatesPath, templates]);

    switch (loading) {
        case LoadingState.Ok:
            return (
                templates && templates.length > 0 ? <Stack>
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
                </Stack> : <MessageBar
                    messageBarType={MessageBarType.info}
                    isMultiline={true}
                >
                    <h3>No templates found</h3>
                    <p>Looks like there aren't any templates registered for this resource type.</p>
                </MessageBar>
            )
        case LoadingState.Error:
            return (
                <ExceptionLayout e={apiError} />
            );
        default:
            return (
                <div style={{ marginTop: 20 }}>
                    <Spinner label="Loading templates" ariaLive="assertive" labelPosition="top" size={SpinnerSize.large} />
                </div>
            )
    }
}
