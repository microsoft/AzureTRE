import { Link, Text } from "@fluentui/react";
import moment from "moment";
import React from "react";
import { Resource } from "../../models/resource";
import { ComplexPropertyModal } from "./ComplexItemDisplay";
import { PropertyGrid, PropertyGridItem, sectionHeaderClass, userDisplayName } from "./ResourceDetailsLayout";

interface ResourcePropertyPanelProps {
  resource: Resource;
}

const friendlyKey = (key: string) => {
  const words = key.replace(/_/g, " ");
  return words.charAt(0).toUpperCase() + words.slice(1).toLowerCase();
};

const friendlyResourceType = (type: string) => friendlyKey(type.replace(/-/g, " "));

export const renderPropertyValue = (val: any, title: string): React.ReactNode => {
  if (val === null || val === undefined || val === "") return "—";
  if (typeof val === "boolean") return val ? "Yes" : "No";
  if (typeof val === "string") {
    if (val.startsWith("https://")) {
      return (
        <Link href={val} target="_blank" rel="noreferrer">
          {val}
        </Link>
      );
    }
    return val;
  }
  if (typeof val === "object") return <ComplexPropertyModal val={val} title={title} />;
  return val.toString();
};

export const ResourcePropertyPanel: React.FunctionComponent<ResourcePropertyPanelProps> = (
  props: ResourcePropertyPanelProps,
) => {
  if (!props.resource || !props.resource.id) return <></>;
  const r = props.resource;

  const resourceItems: Array<PropertyGridItem> = [
    { label: "Resource ID", value: r.id, copyValue: r.id },
    { label: "Resource type", value: friendlyResourceType(r.resourceType) },
    { label: "Resource path", value: r.resourcePath, copyValue: r.resourcePath },
    { label: "Template", value: `${r.templateName} (${r.templateVersion})` },
    { label: "Enabled", value: r.isEnabled ? "Yes" : "No" },
    {
      label: "Last updated",
      value: `${moment.unix(r.updatedWhen).format("LLL")} by ${userDisplayName(r.user)}`,
    },
  ];

  const propertyItems: Array<PropertyGridItem> = Object.keys(r.properties).map((key) => ({
    label: friendlyKey(key),
    value: renderPropertyValue((r.properties as any)[key], friendlyKey(key)),
  }));

  return (
    <div style={{ padding: "0 5px" }}>
      <Text block variant="mediumPlus" className={sectionHeaderClass}>
        Resource
      </Text>
      <PropertyGrid items={resourceItems} />
      <Text block variant="mediumPlus" className={sectionHeaderClass}>
        Properties
      </Text>
      <PropertyGrid items={propertyItems} />
    </div>
  );
};
