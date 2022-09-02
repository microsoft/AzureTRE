import React from "react";
import { Operation } from "../models/operation";

export const OperationsContext = React.createContext({
  operations: [] as Array<Operation>,
  addOperations: (ops: Array<Operation>) => {},
  dismissCompleted: () => {}
});
