import { afterEach, describe, expect, it } from "vitest";
import { act, cleanup, fireEvent, render, renderHook, screen, waitFor } from "@testing-library/react";
import { BrowserRouter, Link, MemoryRouter, useLocation, useNavigate } from "react-router-dom";

const NavigateTo = ({ path }: { path: string }) => {
  const navigate = useNavigate();
  const location = useLocation();
  return (
    <>
      <button onClick={() => navigate(path)}>Open resource</button>
      <output data-testid="destination">{location.pathname}</output>
    </>
  );
};

afterEach(() => {
  cleanup();
  window.history.replaceState(null, "", "/");
});

describe("router URL handling", () => {
  // GHSA-wrjc-x8rr-h8h6: mixed leading separators must not allow navigation
  // to a different origin through an internal resource path.
  it.each(["//", "\\\\", "/\\", "\\/"])("rejects external useNavigate target with separator %j", (prefix) => {
    const { result } = renderHook(() => ({ navigate: useNavigate(), location: useLocation() }), {
      wrapper: MemoryRouter,
    });
    expect(() => {
      act(() => result.current.navigate(prefix + "outside.example.test/resource"));
    }).toThrow("External navigation is not allowed");
    expect(result.current.location.pathname).toBe("/");
  });

  it.each(["//", "\\\\", "/\\", "\\/"])("recognises a same-origin Link with separator %j", async (prefix) => {
    render(
      <BrowserRouter>
        <Link to={prefix + window.location.host + "/workspaces/workspace"}>Notification</Link>
        <NavigateTo path="/" />
      </BrowserRouter>,
    );
    const link = screen.getByRole("link", { name: "Notification" }) as HTMLAnchorElement;
    expect(new URL(link.href).origin).toBe(window.location.origin);
    fireEvent.click(link);
    await waitFor(() => expect(screen.getByTestId("destination").textContent).toBe("/workspaces/workspace"));
  });

  it.each([
    "/workspaces/workspace",
    "/shared-services/shared",
    "/workspaces/workspace/workspace-services/service/user-resources/desktop",
  ])("preserves API-generated resource path %s", async (path) => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <NavigateTo path={path} />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Open resource" }));
    await waitFor(() => expect(screen.getByTestId("destination").textContent).toBe(path));
  });
});
