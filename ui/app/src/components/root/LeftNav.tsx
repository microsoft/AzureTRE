import React, { useContext } from "react";
import { Nav, INavLinkGroup } from "@fluentui/react/lib/Nav";
import { useLocation, useNavigate } from "react-router-dom";
import { AppRolesContext } from "../../contexts/AppRolesContext";
import { RoleName } from "../../models/roleNames";

export const LeftNav: React.FunctionComponent = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const appRolesCtx = useContext(AppRolesContext);

  const isRequestsRoute = location.pathname.startsWith("/requests"); // ← True if URL starts with /requests

  const navLinkGroups: INavLinkGroup[] = [
    {
      links: [
        {
          name: "Workspaces",
          url: "/",
          key: "/",
          icon: "WebAppBuilderFragment",
        },
      ],
    },
  ];

  // show shared-services link if TRE Admin
  if (appRolesCtx.roles.includes(RoleName.TREAdmin)) {
    navLinkGroups[0].links.push({
      name: "Shared Services",
      url: "/shared-services",
      key: "shared-services",
      icon: "Puzzle",
    });
  }

  const requestsLinkArray: {
    name: string;
    url: string;
    key: string;
    icon: string;
  }[] = [];

  requestsLinkArray.push({
    name: "Airlock",
    url: "/requests/airlock",
    key: "airlock",
    icon: "Lock",
  });

  // add Requests link
  navLinkGroups[0].links.push({
    name: "Requests",
    url: "/requests",
    key: "requests",
    icon: "",
    links: requestsLinkArray,
    isExpanded: isRequestsRoute,
  });

  return (
    <Nav
      onLinkClick={(e, item) => {
        e?.preventDefault();
        if (!item || !item.url) return;
        item.isExpanded = true;
        if (item.url !== "/requests") {
          navigate(item.url);
        }
      }}
      ariaLabel="TRE Left Navigation"
      groups={navLinkGroups}
    />
  );
};
