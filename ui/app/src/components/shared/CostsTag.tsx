import { Stack } from "@fluentui/react";
import { useContext } from "react";
import { CostsContext } from "../../contexts/CostsContext";

interface CostsTagProps {
  resourceId: string
}

export const CostsTag: React.FunctionComponent<CostsTagProps> = (props: CostsTagProps) => {
  const costsCtx = useContext(CostsContext);
  const resourceCosts = costsCtx?.costs?.find((resourceCost) => {
    return resourceCost.id === props.resourceId;
  });
  let costBadge = <></>;
  if (resourceCosts && resourceCosts.costs.length > 0) {
    const formattedCost = new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency: resourceCosts?.costs[0].currency,
      currencyDisplay: 'narrowSymbol',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(resourceCosts?.costs[0].cost);
    costBadge = <Stack.Item style={{maxHeight: 18}} className="tre-badge">{formattedCost}</Stack.Item>
  }

  return (costBadge);
}
