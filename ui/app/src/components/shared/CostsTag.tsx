import { Stack, Shimmer, TooltipHost, Icon } from "@fluentui/react";
import { useContext, useEffect, useState } from "react";
import { CostsContext } from "../../contexts/CostsContext";
import { LoadingState } from "../../models/loadingState";
import { WorkspaceContext } from "../../contexts/WorkspaceContext";
import { CostResource } from "../../models/costs";

interface CostsTagProps {
  resourceId: string;
}

export const CostsTag: React.FunctionComponent<CostsTagProps> = (props: CostsTagProps) => {
  const costsCtx = useContext(CostsContext);
  const workspaceCtx = useContext(WorkspaceContext);
  const [loadingState, setLoadingState] = useState(LoadingState.Loading);

  const [formattedCost, setFormattedCost] = useState<string | undefined>(undefined);

  useEffect(() => {
    async function fetchCostData() {
        let costs: CostResource[] = [];
        if (workspaceCtx.costs.length > 0) {
          costs = workspaceCtx.costs
        } else if (costsCtx.costs) {
          costs = costsCtx.costs
        }

        const resourceCosts = costs.find((cost) => {
          return cost.id === props.resourceId;
        });

        if (resourceCosts && resourceCosts.costs.length > 0) {
          const formattedCost = new Intl.NumberFormat(undefined, {
            style: 'currency',
            currency: resourceCosts?.costs[0].currency,
            currencyDisplay: 'narrowSymbol',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
          }).format(resourceCosts.costs[0].cost);
          setFormattedCost(formattedCost);
          setLoadingState(LoadingState.Ok);
        }
      }
      fetchCostData();
  }, [costsCtx.loadingState, props.resourceId, workspaceCtx.costs, costsCtx.costs]);

  const costBadge = (
    <Stack.Item style={{ maxHeight: 18 }} className="tre-badge">
      {loadingState === LoadingState.Loading ? (
        <Shimmer />
      ) : (
        <>
          {formattedCost ? (
            formattedCost
          ) : (
            <TooltipHost content="Cost data not yet available">
              <Icon iconName="Clock" />
            </TooltipHost>
          )}
        </>
      )}
    </Stack.Item>
  );

  return (costBadge);
};
