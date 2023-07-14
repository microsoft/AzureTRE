import { MessageBar, MessageBarType } from "@fluentui/react";
import React from "react";

interface ErrorState {
  hasError: boolean
}

export class GenericErrorBoundary extends React.Component<any, ErrorState, any> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: any) {
    // Update state so the next render will show the fallback UI.
    return { hasError: true };
  }

  componentDidCatch(error: any, errorInfo: any) {
    // You can also log the error to an error reporting service
    console.error('UNHANDLED EXCEPTION', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <MessageBar
          messageBarType={MessageBarType.error}
          isMultiline={false}
        >
          <h3>Uh oh!</h3>
          <p>This area encountered an error that we can't recover from. Please check your configuration and refresh. <br/>
          Further debugging details can be found in the browser console.</p>
        </MessageBar>
      );
    }

    return this.props.children;
  }
}