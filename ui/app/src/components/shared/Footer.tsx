import React from "react";
import { mergeStyles } from "@fluentui/react";

export const Footer: React.FunctionComponent = () => {
  const year = new Date().getFullYear();

  return (
    <footer className={contentClass}>
      © {year} University of Oxford. Research Services, 5 Worcester Street,
      Oxford, OX1 2BX
      <div className="footer-migration-notice">
        Migrating to{" "}
        <a
          href="https://workspace.oxtre.ox.ac.uk"
          target="_blank"
          rel="noreferrer"
        >
          workspace.oxtre.ox.ac.uk
        </a>{" "}
        soon.
      </div>
    </footer>
  );
};

const contentClass = mergeStyles({
  textAlign: "center",
  padding: "1rem",
  color: "#ffffff",
  fontSize: "0.75rem",
  backgroundColor: "#002147",
});
