import React from "react";
import { describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor } from "../../../test-utils";
import { AirlockReviewRequest } from "./AirlockReviewRequest";

const mockApiCall = vi.hoisted(() => vi.fn());
vi.mock("../../../hooks/useAuthApiCall", () => ({
  useAuthApiCall: () => mockApiCall,
  HttpMethod: { Get: "GET", Post: "POST" },
  ResultType: { JSON: "JSON" },
}));
vi.mock("../../../hooks/useComponentManager", () => ({ useComponentManager: () => ({}) }));
const msal = vi.hoisted(() => ({ account: { localAccountId: "reviewer.tenant" }, accounts: [{}] }));
vi.mock("@azure/msal-react", () => ({
  MsalProvider: ({ children }: any) => children,
  useMsal: () => ({ accounts: msal.accounts }),
  useAccount: () => msal.account,
}));

describe("AirlockReviewRequest", () => {
  it("separates the review reason from the approve/reject decision", () => {
    render(
      <AirlockReviewRequest
        request={undefined}
        onUpdateRequest={vi.fn()}
        onReviewRequest={vi.fn()}
        onClose={vi.fn()}
      />,
    );

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

  it("restarts the review when a different request is shown", () => {
    const props = { onUpdateRequest: vi.fn(), onReviewRequest: vi.fn(), onClose: vi.fn() };
    const { rerender } = render(<AirlockReviewRequest request={{ id: "a" } as any} {...props} />);

    fireEvent.click(screen.getByRole("button", { name: "Proceed to review" }));
    fireEvent.change(screen.getByRole("textbox", { name: "Reason for decision" }), {
      target: { value: "Reason for A" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Continue to decision" }));
    expect(screen.getByRole("button", { name: "Approve" })).toBeInTheDocument();

    rerender(<AirlockReviewRequest request={{ id: "b" } as any} {...props} />);

    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
    expect(screen.queryByText("Reason for A")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Proceed to review" })).toBeInTheDocument();
  });

  it("does not let a previous request's slow review VM lookup appear on the next request", async () => {
    let resolveA: (v: unknown) => void = () => undefined;
    mockApiCall.mockImplementation(() => new Promise((r) => (resolveA = r)));
    const workspaceContext = {
      workspace: { id: "ws", properties: { airlock_review_config: { import: {} } } },
      workspaceApplicationIdURI: "scope",
      roles: [],
      costs: [],
      setCosts: vi.fn(),
      setRoles: vi.fn(),
      setWorkspace: vi.fn(),
    };
    const props = { onUpdateRequest: vi.fn(), onReviewRequest: vi.fn(), onClose: vi.fn() };
    const requestA = {
      id: "a",
      type: "import",
      reviewUserResources: { reviewer: { workspaceId: "ws", workspaceServiceId: "svc", userResourceId: "vm-a" } },
    } as any;
    const requestB = { id: "b", type: "import", reviewUserResources: {} } as any;

    const { rerender } = render(<AirlockReviewRequest request={requestA} {...props} />, {
      children: null,
      workspaceContext: workspaceContext as any,
    });
    rerender(<AirlockReviewRequest request={requestB} {...props} />);
    expect(await screen.findByText("Not created")).toBeInTheDocument();

    await act(async () =>
      resolveA({
        userResource: {
          id: "vm-a",
          deploymentStatus: "deployed",
          isEnabled: true,
          azureStatus: { powerState: "VM running" },
          properties: { connection_uri: "https://vm-a" },
        },
      }),
    );
    expect(screen.getByText("Not created")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "View data" })).not.toBeInTheDocument();
  });

  it("does not close the current review when an earlier request's review succeeds late", async () => {
    let resolveReview: (v: unknown) => void = () => undefined;
    mockApiCall.mockImplementation((path: string) =>
      path.endsWith("/review") ? new Promise((r) => (resolveReview = r)) : Promise.resolve({}),
    );
    const props = { onUpdateRequest: vi.fn(), onReviewRequest: vi.fn(), onClose: vi.fn() };
    const request = (id: string) => ({ id, workspaceId: "ws", title: id, reviewUserResources: {} }) as any;
    const { rerender } = render(<AirlockReviewRequest request={request("a")} {...props} />);

    fireEvent.click(screen.getByRole("button", { name: "Proceed to review" }));
    fireEvent.change(screen.getByRole("textbox", { name: "Reason for decision" }), { target: { value: "OK" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue to decision" }));
    fireEvent.click(screen.getByRole("button", { name: "Approve" }));
    fireEvent.click(await screen.findByRole("button", { name: "Yes, Approve" }));
    await waitFor(() => expect(mockApiCall.mock.calls.map((c) => c[0])).toContain("workspaces/ws/requests/a/review"));

    rerender(<AirlockReviewRequest request={request("b")} {...props} />);
    await act(async () => resolveReview({ airlockRequest: { id: "a" } }));

    expect(props.onReviewRequest).not.toHaveBeenCalled();
    expect(props.onUpdateRequest).toHaveBeenCalledWith({ id: "a" });
  });
});
