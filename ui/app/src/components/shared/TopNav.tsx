import React from 'react';
import { getTheme, Icon, mergeStyles, Stack, Theme, createTheme, loadTheme, makeStyles } from '@fluentui/react';
import { Link } from 'react-router-dom';
import { UserMenu } from './UserMenu';
import { NotificationPanel } from './notifications/NotificationPanel';

// Sets the theme for the whole app
const appTheme: Theme = createTheme({
  palette: {
    themeDarker: '#302e2e',
    themeDark: '#484444',
    themeDarkAlt: '#D26A00',
    themePrimary: '#909C3C',
    themeSecondary: '#EC7C0A',
    themeTertiary: '#ED8215',
    themeLight: '#97A75A',
    themeLighter: '#9EB179',
    themeLighterAlt: '#A5BC97',
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
