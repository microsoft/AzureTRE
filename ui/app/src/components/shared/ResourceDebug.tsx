import React from "react";
import { Resource } from "../../models/resource";
import config from "../../config.json";

interface ResourceDebugProps {
  resource: Resource;
}

export const ResourceDebug: React.FunctionComponent<ResourceDebugProps> = (
  props: ResourceDebugProps,
) => {
  return config.debug === true ? (
    <>
      <hr />
      <h3>Debug details:</h3>
      <ul>
        {Object.keys(props.resource).map((key, i) => {
          let val =
            typeof (props.resource as any)[key] === "object"
              ? JSON.stringify((props.resource as any)[key])
              : (props.resource as any)[key].toString();

          return (
            <li key={i}>
              <b>{key}: </b>
              {val}
            </li>
          );
        })}
      </ul>
    </>
  ) : (
    <></>
  );
};
