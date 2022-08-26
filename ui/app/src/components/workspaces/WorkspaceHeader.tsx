import { getTheme, Icon, mergeStyles, Stack } from '@fluentui/react';
import React, { useContext } from 'react';
import { WorkspaceContext } from '../../contexts/WorkspaceContext';

export const WorkspaceHeader: React.FunctionComponent = () => {
  const workspaceCtx = useContext(WorkspaceContext);

  return (
    <>
      <Stack className={contentClass}>
        <Stack.Item className='tre-workspace-header'>
          <h4 style={{fontWeight: '400'}}>
            <Icon iconName="CubeShape" style={{ marginRight: '8px', fontSize: '22px', verticalAlign: 'bottom' }} />
            {workspaceCtx.workspace?.properties?.display_name}
          </h4>
        </Stack.Item>
      </Stack>
    </>
  );
};

const theme = getTheme();
const contentClass = mergeStyles([
  {
    backgroundColor: theme.palette.themeDarker,
    color: theme.palette.white,
    lineHeight: '15px',
    padding: '0 20px',
    boxShadow: '0 1px 8px 0px #ccc'
  }
]);
