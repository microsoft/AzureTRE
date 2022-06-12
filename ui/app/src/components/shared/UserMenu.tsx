import React from 'react';
import { IContextualMenuProps, Persona, PersonaSize, PrimaryButton } from '@fluentui/react';
import { useAccount, useMsal } from '@azure/msal-react';

export const UserMenu: React.FunctionComponent = () => {
  const { instance, accounts } = useMsal();
  const account = useAccount(accounts[0] || {});

  const menuProps: IContextualMenuProps = {
    shouldFocusOnMount: true,
    directionalHint: 6, // bottom right edge
    items: [
      {
        key: 'logout',
        text: 'Logout',
        iconProps: { iconName: 'SignOut' },
        onClick: () => {
          instance.logout(); // will use MSAL to logout and redirect to the /logout page
        }
      }
    ]
  };

  return (
    <div className='tre-user-menu'>
      <PrimaryButton menuProps={menuProps} style={{background:'none', border:'none'}}>
        <Persona
          text={account?.name}
          size={PersonaSize.size32}
          imageAlt={account?.name}
        />
      </PrimaryButton>

    </div>
  );
};


