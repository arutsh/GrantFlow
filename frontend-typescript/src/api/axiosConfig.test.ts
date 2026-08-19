import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { mockPost } = vi.hoisted(() => ({ mockPost: vi.fn() }));

vi.mock("axios", () => {
  const makeInstance = () => {
    // Must be callable (for the retry) and expose interceptors.*.use.
    const instance: any = vi.fn().mockResolvedValue({ data: {} });
    instance.interceptors = {
      request: { use: vi.fn((onFulfilled) => (instance._requestHandler = onFulfilled)) },
      response: {
        use: vi.fn((onFulfilled, onRejected) => {
          instance._responseRejected = onRejected;
        }),
      },
    };
    instance.defaults = { headers: { common: {} } };
    return instance;
  };

  return {
    default: {
      create: vi.fn(makeInstance),
      post: mockPost,
    },
  };
});

import { createAxiosInstance } from "./axiosConfig";

describe("axiosConfig silent refresh write-back", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    mockPost.mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("writes the refreshed token back to sessionStorage when the refresh token came from sessionStorage, even if localStorage holds an unrelated token", async () => {
    // Two tabs: a "remember me" session in localStorage, this tab's own in sessionStorage.
    localStorage.setItem("token", "other-tab-token");
    localStorage.setItem("refreshToken", "other-tab-refresh-token");
    sessionStorage.setItem("token", "expired-token");
    sessionStorage.setItem("refreshToken", "this-tab-refresh-token");

    mockPost.mockResolvedValue({
      data: { access_token: "new-access", refresh_token: "new-refresh" },
    });

    const instance = createAxiosInstance("http://api.test") as any;

    await instance._responseRejected({
      response: { status: 401 },
      config: { url: "/some/protected/endpoint", headers: {} },
    });

    expect(sessionStorage.getItem("token")).toBe("new-access");
    expect(sessionStorage.getItem("refreshToken")).toBe("new-refresh");
    // The other tab's localStorage session must be untouched.
    expect(localStorage.getItem("token")).toBe("other-tab-token");
    expect(localStorage.getItem("refreshToken")).toBe("other-tab-refresh-token");
  });

  it("writes the refreshed token back to localStorage when the refresh token came from localStorage", async () => {
    localStorage.setItem("token", "expired-token");
    localStorage.setItem("refreshToken", "local-refresh-token");

    mockPost.mockResolvedValue({
      data: { access_token: "new-access", refresh_token: "new-refresh" },
    });

    const instance = createAxiosInstance("http://api.test") as any;

    await instance._responseRejected({
      response: { status: 401 },
      config: { url: "/some/protected/endpoint", headers: {} },
    });

    expect(localStorage.getItem("token")).toBe("new-access");
    expect(localStorage.getItem("refreshToken")).toBe("new-refresh");
    expect(sessionStorage.getItem("token")).toBeNull();
  });
});

describe("axiosConfig email-not-verified handling", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    mockPost.mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // jsdom can't observe real navigation, so this only checks the no-refresh part.
  it("does not attempt a silent refresh on a 403 email_not_verified response", async () => {
    localStorage.setItem("refreshToken", "some-refresh-token");
    const instance = createAxiosInstance("http://api.test") as any;

    await instance
      ._responseRejected({
        response: { status: 403, data: { detail: "email_not_verified" } },
        config: { url: "/some/protected/endpoint", headers: {} },
      })
      .catch(() => {});

    expect(mockPost).not.toHaveBeenCalled();
  });

  it("does not intercept a 403 with an unrelated detail", async () => {
    const instance = createAxiosInstance("http://api.test") as any;

    const rejection = instance._responseRejected({
      response: { status: 403, data: { detail: "some_other_reason" } },
      config: { url: "/some/protected/endpoint", headers: {} },
    });

    await expect(rejection).rejects.toMatchObject({ response: { status: 403 } });
    expect(mockPost).not.toHaveBeenCalled();
  });
});
