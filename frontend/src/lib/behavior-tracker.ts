/**
 * User Behavior Tracker — fire-and-forget event recording.
 * Sends events to POST /api/analytics/user-behavior for agent self-improvement.
 */

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

function getAuthToken(): string {
  try {
    const stored = localStorage.getItem("ops-center-auth");
    if (stored) {
      const parsed = JSON.parse(stored);
      return parsed?.state?.user?.token || "";
    }
  } catch {
    /* ignore */
  }
  return "";
}

export function trackBehavior(
  action: string,
  context: string = "",
  metadata: Record<string, unknown> = {},
): void {
  const token = getAuthToken();
  if (!token) return; // not logged in

  const params = new URLSearchParams({ action, context });
  if (Object.keys(metadata).length > 0) {
    params.set("metadata", JSON.stringify(metadata));
  }

  fetch(`${BASE}/api/analytics/user-behavior?${params}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  }).catch(() => {
    /* fire-and-forget */
  });
}
