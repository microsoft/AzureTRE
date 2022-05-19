import React from "react";
import { Operation } from "../../../models/operation";

export const NotificationsContext = React.createContext({
    latestOperation: {} as Operation,
    addOperation: (op: Operation) => {}
});
