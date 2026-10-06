import { MessageBar, MessageBarType, Link as FluentLink, Icon, DefaultButton } from "@fluentui/react";
import React, { useState } from "react";
import { APIError, API_UNAVAILABLE_MESSAGE } from "../../models/exceptions";

interface ExceptionLayoutProps {
  e: APIError;
  onRetry?: () => void;
}

export const ExceptionLayout: React.FunctionComponent<ExceptionLayoutProps> = (props: ExceptionLayoutProps) => {
  const [showDetails, setShowDetails] = useState(false);
  const [showMessageBar, setShowMessageBar] = useState(true);
  const apiUnavailable =
    props.e.status === 408 || props.e.status === 429 || (props.e.status !== undefined && props.e.status >= 500);

  switch (props.e.status) {
    case 403:
      return (
        <MessageBar messageBarType={MessageBarType.error} isMultiline={true}>
          <h3>Access Denied</h3>
          <h4>{props.e.userMessage}</h4>
          <p>{props.e.message}</p>
          <p>Attempted resource: {props.e.endpoint}</p>
        </MessageBar>
      );
    default:
      if (!showMessageBar) return null;
      return (
        showMessageBar && (
          <MessageBar
            messageBarType={MessageBarType.error}
            isMultiline={true}
            onDismiss={() => setShowMessageBar(false)}
            dismissButtonAriaLabel="Close"
          >
            <h3>{apiUnavailable ? API_UNAVAILABLE_MESSAGE : props.e.userMessage}</h3>
            {!apiUnavailable && <p>{props.e.message}</p>}
            {apiUnavailable && (
              <DefaultButton text="Retry" onClick={props.onRetry || (() => window.location.reload())} />
            )}
            <br />

            <FluentLink
              title={showDetails ? "Show less" : "Show more"}
              href="#"
              onClick={() => {
                setShowDetails(!showDetails);
              }}
              style={{ position: "relative", top: "2px", paddingLeft: 0 }}
            >
              {showDetails ? (
                <>
                  <Icon iconName="ChevronUp" aria-label="Expand Details" /> {"Hide Details"}
                </>
              ) : (
                <>
                  <Icon iconName="ChevronDown" aria-label="Collapse Details" /> {"Show Details"}{" "}
                </>
              )}
            </FluentLink>
            {showDetails && (
              <>
                <table
                  style={{
                    border: "1px solid #666",
                    width: "100%",
                    padding: 10,
                    marginTop: 15,
                  }}
                >
                  <tbody>
                    <tr>
                      <td>
                        <b>Endpoint</b>
                      </td>
                      <td>{props.e.endpoint}</td>
                    </tr>
                    <tr>
                      <td>
                        <b>Status Code</b>
                      </td>
                      <td>{props.e.status || "(none)"}</td>
                    </tr>
                    <tr>
                      <td>
                        <b>Stack Trace</b>
                      </td>
                      <td>{props.e.stack}</td>
                    </tr>
                    <tr>
                      <td>
                        <b>Exception</b>
                      </td>
                      <td>{props.e.exception}</td>
                    </tr>
                  </tbody>
                </table>
              </>
            )}
          </MessageBar>
        )
      );
  }
};
