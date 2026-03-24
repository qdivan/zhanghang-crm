import { defineStore } from "pinia";

import { apiClient } from "../api/client";
import type { TokenResponse, UserInfo } from "../types";

const tokenKey = "daizhang_token";
const userKey = "daizhang_user";

type State = {
  token: string;
  user: UserInfo | null;
  ready: boolean;
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
}

function persistSession(token: string, user: UserInfo) {
  window.localStorage.setItem(tokenKey, token);
  window.localStorage.setItem(userKey, JSON.stringify(user));
}

export const useAuthStore = defineStore("auth", {
  state: (): State => ({
    token: "",
    user: null,
    ready: false,
  }),
  getters: {
    isLoggedIn: (state) => Boolean(state.token && state.user),
  },
  actions: {
    async hydrate() {
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

        const meResp = await apiClient.get<UserInfo>("/auth/me", {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        if (!isUserInfo(meResp.data)) {
          throw new Error("invalid me response");
        }
        this.user = meResp.data;
        persistSession(token, meResp.data);
      } catch {
        this.logout();
        return;
      }

      this.ready = true;
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
    },
    logout() {
      this.token = "";
      this.user = null;
      this.ready = true;
      clearAuthStorage();
    },
  },
});
