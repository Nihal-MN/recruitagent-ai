import { describe, expect, it } from "vitest";
import { STAGE_ORDER, STAGE_TONE, timeAgo, titleCase } from "@/lib/format";

describe("format helpers", () => {
  it("timeAgo produces human ranges", () => {
    const now = new Date().toISOString();
    expect(timeAgo(now)).toBe("just now");
    const twoHoursAgo = new Date(Date.now() - 2 * 3600 * 1000).toISOString();
    expect(timeAgo(twoHoursAgo)).toBe("2h ago");
    const threeDaysAgo = new Date(Date.now() - 3 * 86400 * 1000).toISOString();
    expect(timeAgo(threeDaysAgo)).toBe("3d ago");
  });

  it("titleCase turns event types into readable labels", () => {
    expect(titleCase("approval_requested")).toBe("Approval Requested");
    expect(titleCase("stage_moved")).toBe("Stage Moved");
  });

  it("every pipeline stage has a color tone", () => {
    for (const stage of STAGE_ORDER) {
      expect(STAGE_TONE[stage]).toBeTruthy();
    }
  });
});
