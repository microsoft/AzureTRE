import React from 'react';
import { getTheme, Icon, mergeStyles, Stack, Theme, createTheme, loadTheme, makeStyles } from '@fluentui/react';
import { Link } from 'react-router-dom';
import { UserMenu } from './UserMenu';
import { NotificationPanel } from './notifications/NotificationPanel';

// Sets the theme for the whole app
const appTheme: Theme = createTheme({
  palette: {
    themeDarker: '#A35200',
    themeDark: '#BB5E00',
    themeDarkAlt: '#D26A00',
    themePrimary: '#EA7600',
    themeSecondary: '#EC7C0A',
    themeTertiary: '#ED8215',
    themeLight: '#EE8418',
    themeLighter: '#F19231',
    themeLighterAlt: '#F5A049',
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
