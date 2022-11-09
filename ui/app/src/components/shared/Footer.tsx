import React, { useEffect, useState } from 'react';
import { AnimationClassNames, Callout, IconButton, FontWeights, Stack, Text, getTheme, mergeStyles, mergeStyleSets, StackItem } from '@fluentui/react';
import { HttpMethod, useAuthApiCall } from '../../hooks/useAuthApiCall';
import { ApiEndpoint } from '../../models/apiEndpoints';
import config from "../../config.json";

// TODO:
// - change text to link
// - include any small print



export const Footer: React.FunctionComponent = () => {
  const [showInfo, setShowInfo] = useState(false);
  const [apiMetadata, setApiMetadata] = useState({} as any);
  const apiCall = useAuthApiCall();

  useEffect(() => {
    const getMeta = async() => {
      const result = await apiCall(ApiEndpoint.Metadata, HttpMethod.Get);
      setApiMetadata(result);
    }
    getMeta();
  }, [apiCall]);

  return (
    <div className={contentClass}>
      <Stack horizontal>
        <StackItem grow={1}>Azure Trusted Research Environment</StackItem>
        <StackItem><IconButton style={{color:'#fff'}} iconProps={{ iconName: 'Info' }} id="info" onClick={() => setShowInfo(!showInfo)} /></StackItem>
      </Stack>

      {apiMetadata.api_version && showInfo &&
        <Callout
          className={styles.callout}
          ariaLabelledBy="info-label"
          ariaDescribedBy="info-description"
          role="dialog"
          gapSpace={0}
          target="#info"
          onDismiss={() => setShowInfo(false)}
          setInitialFocus
        >
          <Text block variant="xLarge" className={styles.title} id="info-label">
            Azure TRE
          </Text>
          <Text block variant="small" id="version-description">
            <Stack>
              <Stack.Item>
                <Stack horizontal tokens={{ childrenGap: 5 }}>
                  <Stack.Item style={calloutKeyStyles}>API Version:</Stack.Item>
                  <Stack.Item style={calloutValueStyles}>{apiMetadata.api_version}</Stack.Item>
                </Stack>
                <Stack horizontal tokens={{ childrenGap: 5 }}>
                  <Stack.Item style={calloutKeyStyles}>UI Version:</Stack.Item>
                  <Stack.Item style={calloutValueStyles}>{config.version}</Stack.Item>
                </Stack>
              </Stack.Item>
            </Stack>
          </Text>
        </Callout>
      }

    </div>
  );
};

const theme = getTheme();
const contentClass = mergeStyles([
  {
    backgroundColor: theme.palette.themeDark,
    color: theme.palette.white,
    lineHeight: '30px',
    padding: '0 20px',
  },
  AnimationClassNames.scaleUpIn100,
]);



const calloutKeyStyles: React.CSSProperties = {
  width: 120
}

const calloutValueStyles: React.CSSProperties = {
  width: 180
}

const styles = mergeStyleSets({
  button: {
    width: 130,
  },
  callout: {
    width: 350,
    padding: '20px 24px',
  },
  title: {
    marginBottom: 12,
    fontWeight: FontWeights.semilight
  },
  link: {
    display: 'block',
    marginTop: 20,
  }
});
