import React from 'react';
import { AnimationClassNames, getTheme, mergeStyles } from '@fluentui/react';

// TODO:
// - change text to link
// - include any small print

export const Footer: React.FunctionComponent = () => {
  return (
      <div className={contentClass}>
        Azure Trusted Research Environment
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
