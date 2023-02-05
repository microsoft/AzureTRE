import { IconButton, Spinner, Stack, TooltipHost } from "@fluentui/react";
import React, { useState } from "react";
import { Text } from '@fluentui/react/lib/Text';

interface CliCommandProps {
  command: string,
  title: string,
  isLoading: boolean
}

export const CliCommand: React.FunctionComponent<CliCommandProps> = (props: CliCommandProps) => {

  const COPY_TOOL_TIP_DEFAULT_MESSAGE = "Copy to clipboard"
  const [copyToolTipMessage, setCopyToolTipMessage] = useState<string>(COPY_TOOL_TIP_DEFAULT_MESSAGE);

  const handleCopyCommand = () => {
    navigator.clipboard.writeText(props.command);
    setCopyToolTipMessage("Copied")
    setTimeout(() => setCopyToolTipMessage(COPY_TOOL_TIP_DEFAULT_MESSAGE), 3000);
  }

  const renderCommand = () => {
    const commandMatches = props.command.match(/^az\s(\w+(?:\s\w+)*)/);
    const parameterMatches = props.command.match(/--[\w-]+\s+[^\s]+/g)

    if (!commandMatches) {
      return
    }

    const commandWithoutParams = commandMatches[0]

    return <Stack styles={{ root: { padding: "15px", backgroundColor: "#f2f2f2", border: '1px solid #e6e6e6' } }}>
      <code style={{ color: "blue", fontSize: "13px" }}>
        {commandWithoutParams}
      </code>
      <Stack.Item style={{ paddingLeft: "30px" }}>
        {parameterMatches?.map((parameterMatch) => {
          const paramMatch = parameterMatch.match(/(--[\w-]+)(\s+[^\s]+)/);

          if (!paramMatch) {
            return null;
          }

          const param = paramMatch[1];
          const paramValue = paramMatch[2];
          const paramValueIsComment = paramValue.match(/<.*?>/);

          return (
            <div style={{ wordBreak: "break-all", fontSize: "13px" }}>
              <code style={{ color: "teal" }}>{param}</code><code style={{ color: paramValueIsComment ? "firebrick" : "black" }}>{paramValue}</code>
            </div>
          );
        })}
      </Stack.Item>
    </Stack >
  }

  return (
    <Stack>
      <Stack horizontal style={{ backgroundColor: "#e6e6e6", alignItems: 'center' }}>
        <Stack.Item grow style={{ paddingLeft: "10px", height: "100%" }}>
          <Text >{props.title}</Text>
        </Stack.Item>
        <Stack.Item align="end">
          <TooltipHost content={copyToolTipMessage}>
            <IconButton
              iconProps={{ iconName: 'copy' }}
              styles={{ root: { minWidth: '40px' } }}
              onClick={() => { props.command && handleCopyCommand() }} />
          </TooltipHost>
        </Stack.Item>
      </Stack>
      {(!props.isLoading) ? renderCommand() : <Spinner label="Generating command..." style={{ padding: "15px", backgroundColor: "#f2f2f2", border: '1px solid #e6e6e6' }} />}
    </Stack>
  );
}
