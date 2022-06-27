import React from 'react';
import { powerStates } from '../../models/resource';

interface PowerStateBadgeProps {
  state: powerStates
}

export const PowerStateBadge: React.FunctionComponent<PowerStateBadgeProps> = (props: PowerStateBadgeProps) => {

  let stateClass = "tre-power-off";
  if (props.state === powerStates.Running) stateClass = " tre-power-on";

  return (
    <>
      {props.state && <span className="tre-power-badge">
        <span className={stateClass}></span>{props.state}
      </span>}
    </>
  );
};
