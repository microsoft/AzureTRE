import React from 'react';
import { getTheme, Icon, mergeStyles, Stack, Theme, createTheme, loadTheme } from '@fluentui/react';
import { Link } from 'react-router-dom';
import { UserMenu } from './UserMenu';
import { NotificationPanel } from './notifications/NotificationPanel';

const appTheme: Theme = createTheme({
  palette: {
    themePrimary: '#4c79d2',
    themeDark: '#8b9b3c',
  }
});

loadTheme(appTheme);

export const TopNav: React.FunctionComponent = () => {
  return (
    <>
      <div className={contentClass}>
        <Stack horizontal>
          <Stack.Item grow={100}>
            <Link to='/' className='tre-home-link'>
              <Icon iconName="TestBeakerSolid" style={{ marginLeft: '10px', marginRight: '10px', verticalAlign: 'middle' }} />
              <h5 style={{display: 'inline'}}>ARC Azure TRE</h5>
            </Link>
          </Stack.Item>
          <Stack.Item>
            <NotificationPanel />
          </Stack.Item>
          <Stack.Item grow>
            <UserMenu />
          </Stack.Item>
        </Stack>
      </div>
    </>
  );
};

const theme = getTheme();
const contentClass = mergeStyles([
  {
    backgroundColor: theme.palette.themeDark,
    color: theme.palette.white,
    lineHeight: '50px',
    padding: '0 10px 0 10px'
  }
]);
