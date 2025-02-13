import {
  FontWeights,
  getTheme,
  IButtonStyles,
  IconButton,
  IIconProps,
  Link,
  mergeStyleSets,
  Modal,
} from "@fluentui/react";
import React, { useState } from "react";

interface ComplexPropertyModalProps {
  val: any;
  title: string;
}
export const ComplexPropertyModal: React.FunctionComponent<
  ComplexPropertyModalProps
> = (props: ComplexPropertyModalProps) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <Link onClick={() => setIsOpen(true)}>[details]</Link>
      {isOpen && (
        <Modal
          titleAriaId={"modal"}
          isOpen={true}
          onDismiss={() => setIsOpen(false)}
          isBlocking={false}
          containerClassName={contentStyles.container}
        >
          <div className={contentStyles.header}>
            <span id={"modal"}>{props.title}</span>
            <IconButton
              styles={iconButtonStyles}
              iconProps={cancelIcon}
              ariaLabel="Close popup modal"
              onClick={() => setIsOpen(false)}
            />
          </div>
          <div className={contentStyles.body}>
            <NestedDisplayItem
              val={props.val}
              isExpanded={true}
              topLayer={true}
            />
          </div>
        </Modal>
      )}
    </>
  );
};

interface NestedDisplayItemProps {
  val: any;
  isExpanded?: boolean;
  topLayer?: boolean;
}

const NestedDisplayItem: React.FunctionComponent<NestedDisplayItemProps> = (
  props: NestedDisplayItemProps,
) => {
  const [isExpanded, setIsExpanded] = useState(props.isExpanded === true);

  return (
    <>
      {!props.topLayer && (
        <IconButton
          onClick={() => setIsExpanded(!isExpanded)}
          iconProps={{ iconName: isExpanded ? "ChevronUp" : "ChevronDown" }}
        />
      )}
      {isExpanded && (
        <ul className="tre-complex-list">
          {Object.keys(props.val).map((key: string, i) => {
            if (typeof props.val[key] === "object") {
              return (
                <li
                  key={i}
                  className={props.topLayer ? "tre-complex-list-border" : ""}
                >
                  <span style={{ fontSize: "16px" }}>{key}:</span>
                  <NestedDisplayItem val={props.val[key]} isExpanded={false} />
                </li>
              );
            }
            return (
              <li key={i}>
                {isNaN(parseInt(key)) && key + ":"} {props.val[key]}
              </li>
            );
          })}
        </ul>
      )}
    </>
  );
};

const cancelIcon: IIconProps = { iconName: "Cancel" };

const theme = getTheme();
const contentStyles = mergeStyleSets({
  container: {
    display: "flex",
    flexFlow: "column nowrap",
    alignItems: "stretch",
  },
  header: [
    theme.fonts.xxLarge,
    {
      flex: "1 1 auto",
      borderTop: `4px solid ${theme.palette.themePrimary}`,
      color: theme.palette.neutralPrimary,
      display: "flex",
      alignItems: "center",
      fontWeight: FontWeights.semibold,
      padding: "12px 12px 14px 24px",
    },
  ],
  body: {
    flex: "4 4 auto",
    padding: "0 24px 24px 24px",
    overflowY: "hidden",
    selectors: {
      p: { margin: "14px 0" },
      "p:first-child": { marginTop: 0 },
      "p:last-child": { marginBottom: 0 },
    },
  },
});
const iconButtonStyles: Partial<IButtonStyles> = {
  root: {
    color: theme.palette.neutralPrimary,
    marginLeft: "auto",
    marginTop: "4px",
    marginRight: "2px",
  },
  rootHovered: {
    color: theme.palette.neutralDark,
  },
};
