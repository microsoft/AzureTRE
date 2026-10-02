import React from "react";
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "../../../test-utils";
import { AirlockReviewRequest } from "./AirlockReviewRequest";

describe("AirlockReviewRequest", () => {
  it("separates the review reason from the approve/reject decision", () => {
    render(<AirlockReviewRequest request={undefined} onUpdateRequest={vi.fn()} onReviewRequest={vi.fn()} onClose={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Proceed to review" }));
    fireEvent.change(screen.getByRole("textbox", { name: "Reason for decision" }), {
      target: { value: "The data is appropriate." },
    });

    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reject" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Continue to decision" }));

    expect(screen.getByText("Do you wish to approve or reject this Airlock request?")).toBeInTheDocument();
    expect(screen.getByText("The data is appropriate.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Approve" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reject" })).toBeInTheDocument();
  });
});
