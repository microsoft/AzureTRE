import { getTheme, mergeStyles, Stack } from '@fluentui/react';
import React, { useContext } from 'react';
import { WorkspaceContext } from '../../contexts/WorkspaceContext';

export const WorkspaceHeader: React.FunctionComponent = () => {
  const workspaceCtx = useContext(WorkspaceContext);
  
  return (
    <>
      <Stack className={contentClass}>
        <Stack.Item className='tre-workspace-header'>
        <h1>{workspaceCtx.workspace?.properties?.display_name}</h1>
        </Stack.Item>
      </Stack>
    </>
  );
};


const theme = getTheme();
const contentClass = mergeStyles([
  {
    backgroundColor: theme.palette.themeDark,
    color: theme.palette.white,
    lineHeight: '50px',
    padding: '0 20px',
    boxShadow: '0 1px 8px 0px #ccc'
  }
]);