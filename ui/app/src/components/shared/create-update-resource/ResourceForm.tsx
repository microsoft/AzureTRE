import { Spinner, SpinnerSize } from "@fluentui/react";
import { useEffect, useState } from "react";
import { LoadingState } from "../../../models/loadingState";
import { HttpMethod, ResultType, useAuthApiCall } from "../../../hooks/useAuthApiCall";
import Form from "@rjsf/fluent-ui";
import { Operation } from "../../../models/operation";
import { Resource } from "../../../models/resource";
import { ResourceType } from "../../../models/resourceType";
import { APIError } from "../../../models/exceptions";
import { ExceptionLayout } from "../ExceptionLayout";

interface ResourceFormProps {
  templateName: string,
  templatePath: string,
  resourcePath: string,
  updateResource?: Resource,
  onCreateResource: (operation: Operation) => void,
  workspaceApplicationIdURI?: string
}

export const ResourceForm: React.FunctionComponent<ResourceFormProps> = (props: ResourceFormProps) => {
  const [template, setTemplate] = useState<any | null>(null);
  const [formData, setFormData] = useState({});
  const [loading, setLoading] = useState(LoadingState.Loading as LoadingState);
  const [sendingData, setSendingData] = useState(false);
  const apiCall = useAuthApiCall();
  const [apiError, setApiError] = useState({} as APIError);

  useEffect(() => {
    const getFullTemplate = async () => {
      try {
        // Get the full resource template containing the required parameters
        const templateResponse = await apiCall(props.updateResource ? `${props.templatePath}?is_update=true` : props.templatePath, HttpMethod.Get);

        // if it's an update, populate the form with the props that are available in the template
        if (props.updateResource) {
          let d: any = {};
          for (let prop in templateResponse.properties) {
            d[prop] = props.updateResource?.properties[prop];
          }
          setFormData(d);
        }

        setTemplate(templateResponse);
        setLoading(LoadingState.Ok);
      } catch (err: any){
        err.userMessage = "Error retrieving resource template";
        setApiError(err);
        setLoading(LoadingState.Error);
      }
    };

    // Fetch full resource template only if not in state
    if (!template) {
      getFullTemplate();
    }
  }, [apiCall, props.templatePath, template, props.updateResource]);

  const createUpdateResource = async (formData: any) => {
    setSendingData(true);
    let response;
    try
    {
      if (props.updateResource) {
        // only send the properties we're allowed to send
        let d: any = {}
        for (let prop in template.properties) {
          if (!template.properties[prop].readOnly) d[prop] = formData[prop];
        }
        console.log("patching resource", d);
        let wsAuth = props.updateResource.resourceType === ResourceType.WorkspaceService || props.updateResource.resourceType === ResourceType.UserResource;
        response = await apiCall(props.updateResource.resourcePath, HttpMethod.Patch, wsAuth ? props.workspaceApplicationIdURI : undefined, { properties: d }, ResultType.JSON, undefined, undefined, props.updateResource._etag);
      } else {
        const resource = { templateName: props.templateName, properties: formData };
        console.log(resource);
        response = await apiCall(props.resourcePath, HttpMethod.Post, props.workspaceApplicationIdURI, resource, ResultType.JSON);
      }

      setSendingData(false);
      props.onCreateResource(response.operation);
    } catch (err: any) {
      err.userMessage = 'Error sending create / update request';
      setApiError(err);
      setLoading(LoadingState.Error);
      setSendingData(false);
    }
  }

  // use the supplied uiSchema or create a blank one, and set the overview field to textarea manually.
  const uiSchema = (template && template.uiSchema) || {};
  uiSchema.overview = {
    "ui:widget": "textarea"
  }

  // if no specific order has been set, set a generic one with the primary fields at the top
  if (!uiSchema["ui:order"] || uiSchema["ui:order"].length === 0){
    uiSchema["ui:order"] = [
      "display_name",
      "description",
      "overview",
      "*"
    ]
  }

  switch (loading) {
    case LoadingState.Ok:
      return (
        template &&
        <div style={{ marginTop: 20 }}>
          {
            sendingData ?
              <Spinner label="Sending request" ariaLive="assertive" labelPosition="bottom" size={SpinnerSize.large} />
              :
              <Form schema={template} formData={formData} uiSchema={uiSchema} onSubmit={(e: any) => createUpdateResource(e.formData)} />
          }
        </div>
      )
    case LoadingState.Error:
      return (
        <ExceptionLayout e={apiError} />
      );
    default:
      return (
        <div style={{ marginTop: 20 }}>
          <Spinner label="Loading template" ariaLive="assertive" labelPosition="top" size={SpinnerSize.large} />
        </div>
      )
  }
}
