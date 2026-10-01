import { describe, expect, it, vi, afterEach } from "vitest";
import { api, ApiError, API_BASE } from "@/lib/api";

function mockFetch(status: number, body: unknown) {
  return vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("api client", () => {
  it("hits the configured base URL with /api/v1 prefix", async () => {
    const spy = mockFetch(200, { status: "ok" });
    await api.health();
    expect(spy).toHaveBeenCalledWith(`${API_BASE}/api/v1/health`, expect.anything());
  });

  it("parses the backend error envelope into ApiError", async () => {
    mockFetch(409, {
      error: { code: "approval_rejected", message: "This request was rejected.", detail: null },
    });
    await expect(api.approvals.approve(1)).rejects.toMatchObject({
      name: "ApiError",
      code: "approval_rejected",
      status: 409,
    });
  });

  it("raises network_error when the API is unreachable", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("fetch failed"));
    await expect(api.health()).rejects.toBeInstanceOf(ApiError);
    await expect(api.health()).rejects.toMatchObject({ code: "network_error" });
  });

  it("builds trace filters correctly", async () => {
    const spy = mockFetch(200, []);
    await api.traces.list(7, 50);
    expect(spy.mock.calls[0][0]).toBe(`${API_BASE}/api/v1/tool-executions?limit=50&conversation_id=7`);
  });
});
