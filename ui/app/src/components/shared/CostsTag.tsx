import { Stack, Shimmer, TooltipHost, Icon } from "@fluentui/react";
import { useContext } from "react";
import { CostsContext } from "../../contexts/CostsContext";
import { LoadingState } from "../../models/loadingState";

interface CostsTagProps {
  resourceId: string
}

export const CostsTag: React.FunctionComponent<CostsTagProps> = (props: CostsTagProps) => {
  const costsCtx = useContext(CostsContext);
  const resourceCosts = costsCtx?.costs?.find((resourceCost) => {
    return resourceCost.id === props.resourceId;
  });
  let costBadge = <></>;
  switch(costsCtx.loadingState) {
    case LoadingState.Loading:
      costBadge = <Stack.Item style={{maxHeight: 18, width: 30}} className="tre-badge"><Shimmer/></Stack.Item>
      break;
    case LoadingState.Ok:
      if (resourceCosts && resourceCosts.costs.length > 0) {
        const formattedCost = new Intl.NumberFormat(undefined, {
          style: 'currency',
          currency: resourceCosts?.costs[0].currency,
          currencyDisplay: 'narrowSymbol',
          minimumFractionDigits: 2,
          maximumFractionDigits: 2
        }).format(resourceCosts?.costs[0].cost);
        costBadge = <Stack.Item style={{maxHeight: 18}} className="tre-badge">{formattedCost}</Stack.Item>
      } else {
        costBadge = (
          <Stack.Item style={{maxHeight: 18}} className="tre-badge">
            <TooltipHost content="Cost data not yet available">
              <Icon iconName="Clock" />
            </TooltipHost>
          </Stack.Item>
        );
      }
      break;
  }

  return (costBadge);
}
