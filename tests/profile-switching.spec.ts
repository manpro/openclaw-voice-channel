import { test, expect } from "@playwright/test";

const PROFILES = [
  {
    name: "ultra_realtime",
    label: "Ultra Realtime",
    description: "Lagsta latens",
  },
  {
    name: "fast",
    label: "Snabb",
    description: "Lag latens",
  },
  {
    name: "accurate",
    label: "Noggrann",
    description: "Hog kvalitet",
  },
  {
    name: "highest_quality",
    label: "Hogsta Kvalitet",
    description: "Hogsta kvalitet",
  },
];

test.describe("Profile switching", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("page loads with correct heading", async ({ page }) => {
    await expect(
      page.getByRole("heading", { name: /Whisper Transkribering/i })
    ).toBeVisible();
  });

  test("switch through all profiles and measure load times", async ({
    page,
  }) => {
    const results: { profile: string; timeMs: number }[] = [];

    for (const prof of PROFILES) {
      const button = page.getByRole("button", { name: prof.label });
      await expect(button).toBeVisible();

      const start = Date.now();
      await button.click();

      // Wait for the warmup state — the active button should show warming
      // indicators: animate-pulse class OR disabled state (opacity change)
      // Use a flexible check since the warming state includes min 600ms display
      const statusEl = page.getByTestId("profile-status");

      // Status text should show loading message during warmup
      await expect(statusEl).toContainText(/Laddar/i, { timeout: 3000 });

      // Wait for warmup to finish — status should no longer say "Laddar"
      await expect(statusEl).not.toContainText(/Laddar/i, { timeout: 15000 });

      const elapsed = Date.now() - start;
      results.push({ profile: prof.name, timeMs: elapsed });

      // After warmup: button should be active (have ring-2)
      await expect(button).toHaveClass(/ring-2/);

      // Success flash should appear — "Klar" text
      await expect(statusEl).toContainText(/Klar/i, { timeout: 2000 });

      // Description text should eventually show the profile description
      await expect(statusEl).toContainText(prof.description, {
        timeout: 3000,
      });
    }

    // Log results
    console.log("\n=== Profile switch timings ===");
    for (const r of results) {
      console.log(`  ${r.profile}: ${r.timeMs}ms`);
    }
    console.log("==============================\n");
  });
});
