import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PowerStateBadge } from "./PowerStateBadge";
import { VMPowerStates } from "../../models/resource";

describe("PowerStateBadge Component", () => {
    it("renders running state with correct class", () => {
        render(<PowerStateBadge state={VMPowerStates.Running} />);

        const badge = screen.getByText("running");
        expect(badge).toBeInTheDocument();

        const container = badge.closest(".tre-power-badge");
        expect(container).toBeInTheDocument();

        const indicator = container?.querySelector(".tre-power-on");
        expect(indicator).toBeInTheDocument();
    });

    it("renders stopped state with correct class", () => {
        render(<PowerStateBadge state={VMPowerStates.Stopped} />);

        const badge = screen.getByText("stopped");
        expect(badge).toBeInTheDocument();

        const container = badge.closest(".tre-power-badge");
        expect(container).toBeInTheDocument();

        const indicator = container?.querySelector(".tre-power-off");
        expect(indicator).toBeInTheDocument();
    });

    it("renders starting state with correct class", () => {
        render(<PowerStateBadge state={VMPowerStates.Starting} />);

        const badge = screen.getByText("starting");
        expect(badge).toBeInTheDocument();

        const container = badge.closest(".tre-power-badge");
        expect(container).toBeInTheDocument();

        const indicator = container?.querySelector(".tre-power-off");
        expect(indicator).toBeInTheDocument();
    });

    it("renders stopping state with correct class", () => {
        render(<PowerStateBadge state={VMPowerStates.Stopping} />);

        const badge = screen.getByText("stopping");
        expect(badge).toBeInTheDocument();

        const container = badge.closest(".tre-power-badge");
        expect(container).toBeInTheDocument();

        const indicator = container?.querySelector(".tre-power-off");
        expect(indicator).toBeInTheDocument();
    });

    it("renders deallocating state with correct class", () => {
        render(<PowerStateBadge state={VMPowerStates.Deallocating} />);

        const badge = screen.getByText("deallocating");
        expect(badge).toBeInTheDocument();

        const container = badge.closest(".tre-power-badge");
        expect(container).toBeInTheDocument();

        const indicator = container?.querySelector(".tre-power-off");
        expect(indicator).toBeInTheDocument();
    });

    it("renders deallocated state with correct class", () => {
        render(<PowerStateBadge state={VMPowerStates.Deallocated} />);

        const badge = screen.getByText("deallocated");
        expect(badge).toBeInTheDocument();

        const container = badge.closest(".tre-power-badge");
        expect(container).toBeInTheDocument();

        const indicator = container?.querySelector(".tre-power-off");
        expect(indicator).toBeInTheDocument();
    });

    it("strips 'VM ' prefix from state text", () => {
        render(<PowerStateBadge state={VMPowerStates.Running} />);

        // Should show "running" not "VM running"
        expect(screen.getByText("running")).toBeInTheDocument();
        expect(screen.queryByText("VM running")).not.toBeInTheDocument();
    });

    it("renders nothing when state is undefined", () => {
        render(<PowerStateBadge state={undefined as unknown as VMPowerStates} />);

        expect(screen.queryByText(/.+/)).not.toBeInTheDocument();
    });

    it("renders nothing when state is null", () => {
        render(<PowerStateBadge state={null as unknown as VMPowerStates} />);

        expect(screen.queryByText(/.+/)).not.toBeInTheDocument();
    });

    it("renders nothing when state is empty string", () => {
        render(<PowerStateBadge state={"" as unknown as VMPowerStates} />);

        expect(screen.queryByText(/.+/)).not.toBeInTheDocument();
    });
});
