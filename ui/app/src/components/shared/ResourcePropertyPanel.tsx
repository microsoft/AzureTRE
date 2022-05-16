import React from "react";
import { Resource } from "../../models/resource";

interface ResourcePanelProps {
    resource: Resource
}

export const ResourcePropertyPanel: React.FunctionComponent<ResourcePanelProps> = (props: ResourcePanelProps) => {
    return (
        <>
            <h3>Resource property panel - {props.resource.id}</h3>
        </>
    );
};