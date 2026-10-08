import {
  DetailsList,
  DetailsListLayoutMode,
  getTheme,
  IColumn,
  SelectionMode,
  Spinner,
  SpinnerSize,
  Stack,
  Text,
  TooltipHost,
} from "@fluentui/react";
import React, { useEffect, useContext, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { HttpMethod, useAuthApiCall } from "../../hooks/useAuthApiCall";
import { HistoryItem, Resource } from "../../models/resource";
import { ApiEndpoint } from "../../models/apiEndpoints";
import { WorkspaceContext } from "../../contexts/WorkspaceContext";
import { getListApiScope } from "./ResourceDetailsLayout";
import config from "../../config.json";
import { APIError } from "../../models/exceptions";
import { LoadingState } from "../../models/loadingState";
import { ExceptionLayout } from "./ExceptionLayout";
import { RelativeTime, userDisplayName } from "./ResourceDetailsLayout";

interface ResourceHistoryListProps {
  resource: Resource;
  // Roles that grant access to this list. The workspace token is used only when a workspace role grants it, so a
  // TRE Administrator who also holds another workspace role still calls the API with the core (TREAdmin) token.
  allowedRoles?: Array<string>;
}

const theme = getTheme();

interface HistoryRow extends HistoryItem {
  isCurrent: boolean;
  changes: Array<{ label: string; from: string; to: string }> | null;
}

const friendlyKey = (key: string) => {
  const words = key.replace(/_/g, " ");
  return words.charAt(0).toUpperCase() + words.slice(1).toLowerCase();
};

const EMPTY = "";

const formatValue = (val: any): string => {
  if (val === null || val === undefined || val === "") return EMPTY;
  if (typeof val === "boolean") return val ? "Yes" : "No";
  if (typeof val === "object") return JSON.stringify(val);
  return String(val);
};

// What changed between two snapshots of a resource. Null for the first version.
export const diffSnapshots = (previous: HistoryItem | undefined, current: HistoryItem) => {
  if (!previous) return null;
  const changes: Array<{ label: string; from: string; to: string }> = [];
  if (previous.isEnabled !== current.isEnabled) {
    changes.push({ label: "Enabled", from: formatValue(previous.isEnabled), to: formatValue(current.isEnabled) });
  }
  if (previous.templateVersion !== current.templateVersion) {
    changes.push({
      label: "Template version",
      from: formatValue(previous.templateVersion),
      to: formatValue(current.templateVersion),
    });
  }
  const before = previous.properties || {};
  const after = current.properties || {};
  Array.from(new Set([...Object.keys(before), ...Object.keys(after)])).forEach((key) => {
    if (JSON.stringify(before[key]) !== JSON.stringify(after[key])) {
      changes.push({ label: friendlyKey(key), from: formatValue(before[key]), to: formatValue(after[key]) });
    }
  });
  return changes;
};

const truncate = (text: string, max = 60) => (text.length > max ? `${text.slice(0, max)}…` : text);

// Added values show just the new value, cleared values show "removed", and only real changes show old → new.
const describeChange = (c: { from: string; to: string }, short: boolean) => {
  const t = (v: string) => (short ? truncate(v) : v);
  if (c.from === EMPTY) return t(c.to);
  if (c.to === EMPTY) return `removed (was ${t(c.from)})`;
  return `${t(c.from)} → ${t(c.to)}`;
};

const ChangesCell: React.FunctionComponent<{ row: HistoryRow }> = ({ row }) => {
  if (row.changes === null) return <Text>Created</Text>;
  if (row.changes.length === 0)
    return <Text style={{ color: theme.palette.neutralSecondary }}>No property changes</Text>;
  return (
    <Stack tokens={{ childrenGap: 2 }}>
      {row.changes.map((c) => (
        <TooltipHost key={c.label} content={describeChange(c, false)}>
          <Text variant="small">
            <b>{c.label}</b>: {describeChange(c, true)}
          </Text>
        </TooltipHost>
      ))}
    </Stack>
  );
};

const columns: Array<IColumn> = [
  {
    key: "version",
    name: "Version",
    minWidth: 70,
    maxWidth: 90,
    onRender: (h: HistoryRow) => (h.isCurrent ? `${h.resourceVersion} (current)` : h.resourceVersion),
  },
  {
    key: "updated",
    name: "Updated",
    minWidth: 100,
    maxWidth: 130,
    onRender: (h: HistoryRow) => <RelativeTime unixTime={h.updatedWhen} />,
  },
  {
    key: "user",
    name: "By",
    minWidth: 120,
    maxWidth: 220,
    isMultiline: true,
    onRender: (h: HistoryRow) => userDisplayName(h.user),
  },
  {
    key: "changes",
    name: "Changes",
    minWidth: 240,
    isMultiline: true,
    onRender: (h: HistoryRow) => <ChangesCell row={h} />,
  },
];

export const ResourceHistoryList: React.FunctionComponent<ResourceHistoryListProps> = (
  props: ResourceHistoryListProps,
) => {
  const apiCall = useAuthApiCall();
  const [apiError, setApiError] = useState({} as APIError);
  const workspaceCtx = useContext(WorkspaceContext);
  const { resourceId } = useParams();
  const [resourceHistory, setResourceHistory] = useState([] as Array<HistoryItem>);
  const [loadingState, setLoadingState] = useState("loading");

  useEffect(() => {
    const getResourceHistory = async () => {
      try {
        const scopeId = getListApiScope(workspaceCtx.roles, workspaceCtx.workspaceApplicationIdURI, props.allowedRoles);
        const history = await apiCall(`${props.resource.resourcePath}/${ApiEndpoint.History}`, HttpMethod.Get, scopeId);
        config.debug &&
          console.log(`Got resource history, for resource:${props.resource.id}: ${history.resource_history}`);
        setResourceHistory(history.resource_history);
        setLoadingState(history ? LoadingState.Ok : LoadingState.Error);
      } catch (err: any) {
        err.userMessage = "Error retrieving resource history";
        setApiError(err);
        setLoadingState(LoadingState.Error);
      }
    };
    getResourceHistory();
  }, [
    apiCall,
    props.resource,
    resourceId,
    workspaceCtx.workspaceApplicationIdURI,
    workspaceCtx.roles,
    props.allowedRoles,
  ]);

  // History holds earlier snapshots; add the current state so the latest change is shown too.
  const rows = useMemo(() => {
    const current: HistoryItem = {
      id: "current",
      resourceId: props.resource.id,
      isEnabled: props.resource.isEnabled,
      resourceVersion: props.resource.resourceVersion,
      updatedWhen: props.resource.updatedWhen,
      user: props.resource.user,
      properties: props.resource.properties,
      templateVersion: props.resource.templateVersion,
    };
    const snapshots = [...resourceHistory].sort((a, b) => a.resourceVersion - b.resourceVersion);
    if (!snapshots.some((h) => h.resourceVersion === current.resourceVersion)) snapshots.push(current);
    return snapshots
      .map((h, i) => ({
        ...h,
        isCurrent: h.resourceVersion === current.resourceVersion,
        changes: diffSnapshots(snapshots[i - 1], h),
      }))
      .reverse();
  }, [resourceHistory, props.resource]);

  switch (loadingState) {
    case LoadingState.Ok:
      return (
        <DetailsList
          items={rows}
          columns={columns}
          selectionMode={SelectionMode.none}
          layoutMode={DetailsListLayoutMode.justified}
          compact
          onShouldVirtualize={() => false}
          ariaLabelForGrid="Resource history"
        />
      );
    case LoadingState.Error:
      return <ExceptionLayout e={apiError} />;
    default:
      return (
        <div style={{ marginTop: "20px" }}>
          <Spinner label="Loading history" ariaLive="assertive" labelPosition="top" size={SpinnerSize.large} />
        </div>
      );
  }
};
