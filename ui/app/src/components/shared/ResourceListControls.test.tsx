import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { defaultSortOptions, useResourceListFilter } from "./ResourceListControls";
import { Resource } from "../../models/resource";

const res = (id: string, name: string, status: string, updatedWhen: number) =>
  ({ id, properties: { display_name: name }, deploymentStatus: status, updatedWhen }) as unknown as Resource;

const resources = [
  res("b", "VM 10", "deployed", 2),
  res("a", "VM 2", "deployment_failed", 3),
  res("c", "Alpha", "deployed", 1),
];
const sortOptions = defaultSortOptions<Resource>();

describe("useResourceListFilter", () => {
  beforeEach(() => localStorage.clear());

  it("sorts by name naturally and toggles direction", () => {
    const { result } = renderHook(() => useResourceListFilter(resources, { storageKey: "test", sortOptions }));
    expect(result.current.visibleResources.map((r) => r.id)).toEqual(["c", "a", "b"]);

    act(() => result.current.controlsProps.onSortChange("name"));
    expect(result.current.visibleResources.map((r) => r.id)).toEqual(["b", "a", "c"]);
  });

  it("searches names, IDs and status", () => {
    const { result } = renderHook(() => useResourceListFilter(resources, { storageKey: "test", sortOptions }));

    act(() => result.current.controlsProps.onSearchChange("failed"));
    expect(result.current.visibleResources.map((r) => r.id)).toEqual(["a"]);

    act(() => result.current.controlsProps.onSearchChange("alpha"));
    expect(result.current.visibleResources.map((r) => r.id)).toEqual(["c"]);

    act(() => result.current.controlsProps.onSearchChange("deployment failed"));
    expect(result.current.visibleResources.map((r) => r.id)).toEqual(["a"]);
  });

  it("matches names anywhere but IDs only from the start", () => {
    const uuidResources = [
      res("3de133f4-805d-45e3-9ff1-a6ef5b13487e", "Cloud-account owned VM", "deployed", 1),
      res("11111111-2222-4333-8444-555555555555", "pr5100-scale-4", "deployed", 2),
    ];
    const { result } = renderHook(() => useResourceListFilter(uuidResources, { storageKey: "test", sortOptions }));

    act(() => result.current.controlsProps.onSearchChange("-4"));
    expect(result.current.visibleResources.map((r) => r.properties.display_name)).toEqual(["pr5100-scale-4"]);

    act(() => result.current.controlsProps.onSearchChange("3de1"));
    expect(result.current.visibleResources.map((r) => r.properties.display_name)).toEqual(["Cloud-account owned VM"]);
  });

  it("remembers the sort choice per list", () => {
    const first = renderHook(() => useResourceListFilter(resources, { storageKey: "test", sortOptions }));
    act(() => first.result.current.controlsProps.onSortChange("updated"));
    first.unmount();

    const second = renderHook(() => useResourceListFilter(resources, { storageKey: "test", sortOptions }));
    expect(second.result.current.controlsProps.sortKey).toBe("updated");
    expect(second.result.current.visibleResources.map((r) => r.id)).toEqual(["c", "b", "a"]);
  });
});
