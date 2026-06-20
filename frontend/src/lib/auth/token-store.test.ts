import { beforeEach, describe, expect, it, vi } from "vitest";

import { tokenStore } from "./token-store";

describe("tokenStore", () => {
  beforeEach(() => {
    tokenStore.clear();
  });

  it("keeps the access token in memory and the refresh token in localStorage", () => {
    tokenStore.setTokens("access-1", "refresh-1");
    expect(tokenStore.getAccessToken()).toBe("access-1");
    expect(tokenStore.getRefreshToken()).toBe("refresh-1");
    expect(localStorage.getItem("seedbank.refresh_token")).toBe("refresh-1");
    expect(tokenStore.hasSession()).toBe(true);
  });

  it("clears both tokens", () => {
    tokenStore.setTokens("a", "b");
    tokenStore.clear();
    expect(tokenStore.getAccessToken()).toBeNull();
    expect(tokenStore.getRefreshToken()).toBeNull();
    expect(tokenStore.hasSession()).toBe(false);
  });

  it("notifies subscribers on change and unsubscribes cleanly", () => {
    const listener = vi.fn();
    const unsub = tokenStore.subscribe(listener);
    tokenStore.setTokens("a", "b");
    expect(listener).toHaveBeenCalledTimes(1);
    unsub();
    tokenStore.clear();
    expect(listener).toHaveBeenCalledTimes(1);
  });
});
