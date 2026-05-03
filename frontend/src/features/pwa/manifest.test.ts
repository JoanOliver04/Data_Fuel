import { describe, expect, it } from "vitest";

import { pwaManifest } from "./manifest";

describe("pwaManifest", () => {
  it("declares required PWA fields", () => {
    expect(pwaManifest.name).toBe("Data Fuel");
    expect(pwaManifest.short_name).toBe("DataFuel");
    expect(pwaManifest.start_url).toBe("/");
    expect(pwaManifest.display).toBe("standalone");
    expect(pwaManifest.scope).toBe("/");
  });

  it("uses primary brand color for theme", () => {
    expect(pwaManifest.theme_color).toMatch(/^#[0-9A-F]{6}$/i);
    expect(pwaManifest.background_color).toMatch(/^#[0-9A-F]{6}$/i);
  });

  it("provides at least one any-purpose and one maskable icon", () => {
    const icons = pwaManifest.icons ?? [];
    const any = icons.find((i) => (i.purpose ?? "any").includes("any"));
    const maskable = icons.find((i) => (i.purpose ?? "").includes("maskable"));

    expect(any).toBeDefined();
    expect(maskable).toBeDefined();
  });

  it("ships square PNG icons covering 192x192 and 512x512", () => {
    const icons = pwaManifest.icons ?? [];
    expect(icons.length).toBeGreaterThan(0);

    const sizes = icons.map((i) => i.sizes);
    expect(sizes).toContain("192x192");
    expect(sizes).toContain("512x512");

    for (const icon of icons) {
      expect(icon.type).toBe("image/png");
      expect(icon.src).toMatch(/^\//);
      expect(icon.sizes).toMatch(/^(\d+)x\1$/);
    }
  });

  it("ships at least one wide and one narrow screenshot for richer install UI", () => {
    const screenshots = pwaManifest.screenshots ?? [];
    const wide = screenshots.find((s) => s.form_factor === "wide");
    const narrow = screenshots.find((s) => s.form_factor === "narrow");

    expect(wide).toBeDefined();
    expect(narrow).toBeDefined();
    for (const shot of screenshots) {
      expect(shot.src).toMatch(/^\//);
      expect(shot.sizes).toMatch(/^\d+x\d+$/);
      expect(shot.label).toBeTruthy();
    }
  });
});
