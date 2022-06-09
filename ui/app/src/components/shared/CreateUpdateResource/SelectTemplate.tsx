import { DefaultButton, MessageBar, MessageBarType, Spinner, SpinnerSize, Stack } from "@fluentui/react";
import { useEffect, useState } from "react";
import { LoadingState } from "../../../models/loadingState";
import { HttpMethod, useAuthApiCall } from "../../../hooks/useAuthApiCall";

interface SelectTemplateProps {
    templatesPath: string,
    onSelectTemplate: (templateName: string) => void
}

export const SelectTemplate: React.FunctionComponent<SelectTemplateProps> = (props: SelectTemplateProps) => {
    const [templates, setTemplates] = useState<any[] | null>(null);
    const [loading, setLoading] = useState(LoadingState.Loading as LoadingState);
    const apiCall = useAuthApiCall();

    useEffect(() => {
        const getTemplates = async () => {
            try {
                // Get the templates from the API
                const templatesResponse = await apiCall(props.templatesPath, HttpMethod.Get);
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
                templates ? <Stack style={{ marginTop: 20 }}>
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
                    <p>There was an error retrieving resource templates. Please see the browser console for details.</p>
                </MessageBar>
            );
        default:
            return (
                <div style={{ marginTop: 20 }}>
                    <Spinner label="Loading templates" ariaLive="assertive" labelPosition="top" size={SpinnerSize.large} />
                </div>
            )
    }
}
