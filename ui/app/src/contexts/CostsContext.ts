import { createContext } from "react";
import { CostResource } from "../models/costs";

export const CostsContext = createContext({
  costs: [] as Array<CostResource>,
  setCosts: (costs: Array<CostResource>) => { },
});
