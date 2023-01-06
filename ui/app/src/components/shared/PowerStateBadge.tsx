import React from 'react';
import { VMPowerStates } from '../../models/resource';

interface PowerStateBadgeProps {
  state: VMPowerStates
}

export const PowerStateBadge: React.FunctionComponent<PowerStateBadgeProps> = (props: PowerStateBadgeProps) => {
  let stateClass = "tre-power-off";
  if (props.state === VMPowerStates.Running) stateClass = " tre-power-on";

  return (
    <>
      {
        props.state && <span className="tre-power-badge">
          <span className={stateClass}></span>
          <small>{props.state.replace('VM ', '')}</small>
        </span>
      }
    </>
  );
};
