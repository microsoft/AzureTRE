import React from "react";
import { CreateFormResource } from "../models/resourceType";

export const CreateUpdateResourceContext = React.createContext({
  openCreateForm: (createFormResource: CreateFormResource) => {},
});
