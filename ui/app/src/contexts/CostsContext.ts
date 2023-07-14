import { createContext } from "react";
import { CostResource } from "../models/costs";
import { LoadingState } from "../models/loadingState";

export const CostsContext = createContext({
  costs: [] as Array<CostResource>,
  loadingState: {} as LoadingState,
  setCosts: (costs: Array<CostResource>) => { },
  setLoadingState: (loadingState: LoadingState) => {},
});
