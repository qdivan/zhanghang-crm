import { defineStore } from "pinia";

import { apiClient } from "../api/client";
import type { AuthProviders, SsoExchangeResponse, TokenResponse, UserInfo } from "../types";

const tokenKey = "daizhang_token";
const userKey = "daizhang_user";
const sessionRefreshedAtKey = "daizhang_user_refreshed_at";
const SESSION_REFRESH_TTL_MS = 5 * 60 * 1000;

let refreshSessionPromise: Promise<void> | null = null;

type State = {
  token: string;
  user: UserInfo | null;
  ready: boolean;
  providers: AuthProviders | null;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isUserInfo(value: unknown): value is UserInfo {
  if (!isRecord(value)) return false;
  return (
    typeof value.id === "number" &&
    typeof value.username === "string" &&
    typeof value.role === "string" &&
    typeof value.auth_source === "string" &&
    typeof value.ldap_dn === "string" &&
    Array.isArray(value.granted_read_modules) &&
    (typeof value.manager_user_id === "number" || value.manager_user_id === null) &&
    typeof value.manager_username === "string" &&
    typeof value.is_active === "boolean" &&
    typeof value.created_at === "string" &&
    (typeof value.last_login_at === "string" || value.last_login_at === null)
  );
}

function clearAuthStorage() {
  window.localStorage.removeItem(tokenKey);
  window.localStorage.removeItem(userKey);
  window.localStorage.removeItem(sessionRefreshedAtKey);
}

function persistSession(token: string, user: UserInfo, refreshedAt = Date.now()) {
  window.localStorage.setItem(tokenKey, token);
  window.localStorage.setItem(userKey, JSON.stringify(user));
  window.localStorage.setItem(sessionRefreshedAtKey, String(refreshedAt));
}

function shouldRefreshSession(): boolean {
  const raw = window.localStorage.getItem(sessionRefreshedAtKey);
  const refreshedAt = Number(raw);
  if (!Number.isFinite(refreshedAt)) return true;
  return Date.now() - refreshedAt > SESSION_REFRESH_TTL_MS;
}

export const useAuthStore = defineStore("auth", {
  state: (): State => ({
    token: "",
    user: null,
    ready: false,
    providers: null,
  }),
  getters: {
    isLoggedIn: (state) => Boolean(state.token && state.user),
  },
  actions: {
    async hydrate() {
      if (this.ready) return;

      const token = window.localStorage.getItem(tokenKey);
      const userRaw = window.localStorage.getItem(userKey);
      if (!token || token === "undefined" || token === "null" || !userRaw) {
        this.logout();
        return;
      }

      try {
        const parsed = JSON.parse(userRaw);
        if (!isUserInfo(parsed)) {
          throw new Error("invalid stored user");
        }
        this.token = token;
        this.user = parsed;
      } catch {
        this.logout();
        return;
      }

      this.ready = true;

      if (shouldRefreshSession()) {
        void this.refreshCurrentUser(token);
      }
    },
    async refreshCurrentUser(tokenOverride?: string) {
      const token = tokenOverride ?? this.token;
      if (!token) return;
      if (refreshSessionPromise) {
        return refreshSessionPromise;
      }

      refreshSessionPromise = (async () => {
        try {
          const meResp = await apiClient.get<UserInfo>("/auth/me", {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          });
          if (!isUserInfo(meResp.data)) {
            throw new Error("invalid me response");
          }
          if (this.token !== token) return;
          this.user = meResp.data;
          persistSession(token, meResp.data);
        } catch {
          if (this.token === token) {
            this.logout();
          }
        } finally {
          refreshSessionPromise = null;
        }
      })();

      return refreshSessionPromise;
    },
    async login(username: string, password: string) {
      const tokenResp = await apiClient.post<TokenResponse>("/auth/login", {
        username,
        password,
      });
      const token = isRecord(tokenResp.data) && typeof tokenResp.data.access_token === "string"
        ? tokenResp.data.access_token
        : "";
      if (!token) {
        this.logout();
        throw new Error("invalid login response");
      }

      const loginUser = isRecord(tokenResp.data) && isUserInfo(tokenResp.data.user)
        ? tokenResp.data.user
        : null;
      if (!loginUser) {
        const meResp = await apiClient.get<UserInfo>("/auth/me", {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        if (!isUserInfo(meResp.data)) {
          this.logout();
          throw new Error("invalid me response");
        }
        this.token = token;
        this.user = meResp.data;
        this.ready = true;
        persistSession(this.token, this.user);
        return;
      }

      if (!isUserInfo(loginUser)) {
        this.logout();
        throw new Error("invalid login user");
      }

      this.token = token;
      this.user = loginUser;
      this.ready = true;
      persistSession(this.token, this.user);
    },
    async fetchProviders(force = false) {
      if (this.providers && !force) return this.providers;
      const resp = await apiClient.get<AuthProviders>("/auth/providers");
      this.providers = resp.data;
      return this.providers;
    },
    startSsoLogin() {
      const loginUrl = apiClient.getUri({ url: "/auth/sso/login" });
      window.location.href = loginUrl;
    },
    async exchangeSsoTicket(ticket: string) {
      const resp = await apiClient.post<SsoExchangeResponse>("/auth/sso/exchange", {
        ticket,
      });
      const data = resp.data;
      if (data.status === "SUCCESS" && data.access_token && data.user && isUserInfo(data.user)) {
        this.token = data.access_token;
        this.user = data.user;
        this.ready = true;
        persistSession(this.token, this.user);
      }
      return data;
    },
    logout() {
      this.token = "";
      this.user = null;
      this.ready = true;
      clearAuthStorage();
    },
  },
});
