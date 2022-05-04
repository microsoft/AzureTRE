import React from 'react';
import { getTheme, mergeStyles } from '@fluentui/react';
import { Link } from 'react-router-dom';


export const TopNav: React.FunctionComponent = () => {
  return (
      <div className={contentClass}>
        <Link to='/' className='tre-home-link'>Azure TRE</Link>
      </div>
  );
};

const theme = getTheme();
const contentClass = mergeStyles([
  {
    backgroundColor: theme.palette.themeDark,
    color: theme.palette.white,
    lineHeight: '50px',
    padding: '0 20px',
  }
]);