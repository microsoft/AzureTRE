import React from 'react';
import { failedStates, inProgressStates, successStates } from '../../models/operation';

interface StatusBadgeProps {
  status: string
}

export const StatusBadge: React.FunctionComponent<StatusBadgeProps> = (props: StatusBadgeProps) => {

  let baseClass = "tre-badge";
  if (inProgressStates.indexOf(props.status) !== -1) baseClass += " tre-badge-in-progress";
  if (successStates.indexOf(props.status) !== -1) baseClass += " tre-badge-success";
  if (failedStates.indexOf(props.status) !== -1) baseClass += " tre-badge-failed";

  return (
    <>
     {props.status && <span className={baseClass}>{props.status.replace("_", " ")}</span>}
    </>
  );
};
