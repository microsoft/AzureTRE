import React from "react";

export const AppRolesContext = React.createContext({
  roles: [] as Array<string>,
  setAppRoles: (roles: Array<string>) => { }
});
