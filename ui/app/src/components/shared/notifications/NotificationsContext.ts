import React from "react";
import { Operation } from "../../../models/operation";

export const NotificationsContext = React.createContext({
    operations: [] as Array<Operation>,
    addOperation: (op: Operation) => {}
  });