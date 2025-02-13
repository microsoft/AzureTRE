import React, { useContext } from "react";
import { WorkspaceContext } from "../../contexts/WorkspaceContext";
import { Resource } from "../../models/resource";
import { Workspace } from "../../models/workspace";
import { useComponentManager } from "../../hooks/useComponentManager";
import { ResourceHeader } from "../shared/ResourceHeader";
import { useNavigate } from "react-router-dom";
import { ResourceBody } from "../shared/ResourceBody";

export const WorkspaceItem: React.FunctionComponent = () => {
  const workspaceCtx = useContext(WorkspaceContext);
  const navigate = useNavigate();

  const latestUpdate = useComponentManager(
    workspaceCtx.workspace,
    (r: Resource) => workspaceCtx.setWorkspace(r as Workspace),
    (r: Resource) => navigate(`/`),
  );

  return (
    <>
      <ResourceHeader
        resource={workspaceCtx.workspace}
        latestUpdate={latestUpdate}
      />
      <ResourceBody resource={workspaceCtx.workspace} />
    </>
  );
};
