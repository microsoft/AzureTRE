import { Stack, Shimmer, TooltipHost, Icon } from "@fluentui/react";
import { useContext, useEffect, useState } from "react";
import { CostsContext } from "../../contexts/CostsContext";
import { LoadingState } from "../../models/loadingState";
import { WorkspaceContext } from "../../contexts/WorkspaceContext";
import { CostResource } from "../../models/costs";
import {
  useAuthApiCall,
  HttpMethod,
  ResultType,
} from "../../hooks/useAuthApiCall";
import { ApiEndpoint } from "../../models/apiEndpoints";
import { ResourceType } from "../../models/resourceType";

interface CostsTagProps {
  resourceId: string;
  resourceType?: ResourceType;
}

export const CostsTag: React.FunctionComponent<CostsTagProps> = (
  props: CostsTagProps,
) => {
  const costsCtx = useContext(CostsContext);
  const workspaceCtx = useContext(WorkspaceContext);
  const [loadingState, setLoadingState] = useState(LoadingState.Loading);
  const apiCall = useAuthApiCall();
  const [formattedCost, setFormattedCost] = useState<string | undefined>(
    undefined,
  );

  useEffect(() => {
    async function fetchCostData() {
      let costs: CostResource[] = [];
      if (workspaceCtx.costs.length > 0) {
        costs = workspaceCtx.costs;
      } else if (costsCtx.costs.length > 0) {
        costs = costsCtx.costs;
      } else if (!workspaceCtx.workspace.id) {
        let scopeId = (
          await apiCall(
            `${ApiEndpoint.Workspaces}/${props.resourceId}/scopeid`,
            HttpMethod.Get,
          )
        ).workspaceAuth.scopeId;
        const r = await apiCall(
          `${ApiEndpoint.Workspaces}/${props.resourceId}/${ApiEndpoint.Costs}`,
          HttpMethod.Get,
          scopeId,
          undefined,
          ResultType.JSON,
        );
        costs = [{ costs: r.costs, id: r.id, name: r.name }];
      }

      const resourceCosts = costs.find((cost) => {
        return cost.id === props.resourceId;
      });

      if (resourceCosts && resourceCosts.costs.length > 0) {
        const formattedCost = new Intl.NumberFormat(undefined, {
          style: "currency",
          currency: resourceCosts?.costs[0].currency,
          currencyDisplay: "narrowSymbol",
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        }).format(resourceCosts.costs[0].cost);
        setFormattedCost(formattedCost);
      }
      setLoadingState(LoadingState.Ok);
    }
    fetchCostData();
  }, [
    apiCall,
    props.resourceId,
    workspaceCtx.costs,
    costsCtx.costs,
    workspaceCtx.workspace.id,
  ]);

  // Generate tooltip content based on resource type and cost availability
  const getTooltipContent = () => {
    if (!formattedCost) {
      return "Cost data not yet available";
    }

    let baseMessage = "Month-to-date costs";
    
    if (props.resourceType === ResourceType.Workspace) {
      baseMessage += " (includes all workspace services and user resources)";
    }
    
    return baseMessage;
  };

  const costBadge = (
    <Stack.Item style={{ maxHeight: 18 }} className="tre-badge">
      {loadingState === LoadingState.Loading ? (
        <Shimmer />
      ) : (
        <>
          {formattedCost ? (
            <TooltipHost content={getTooltipContent()}>
              {formattedCost}
            </TooltipHost>
          ) : (
            <TooltipHost content={getTooltipContent()}>
              <Icon iconName="Clock" />
            </TooltipHost>
          )}
        </>
      )}
    </Stack.Item>
  );

  return costBadge;
};
