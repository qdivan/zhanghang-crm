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

export const useAuthStore = defineStore("auth", {
  state: (): State => ({
    token: "",
    user: null,
    ready: false,
  }),
  getters: {
    isLoggedIn: (state) => Boolean(state.token),
  },
  actions: {
    hydrate() {
      this.token = window.localStorage.getItem(tokenKey) ?? "";
      const userRaw = window.localStorage.getItem(userKey);
      this.user = userRaw ? (JSON.parse(userRaw) as UserInfo) : null;
      this.ready = true;
    },
    async login(username: string, password: string) {
      const tokenResp = await apiClient.post<TokenResponse>("/auth/login", {
        username,
        password,
      });
      this.token = tokenResp.data.access_token;
      window.localStorage.setItem(tokenKey, this.token);

      const meResp = await apiClient.get<UserInfo>("/auth/me");
      this.user = meResp.data;
      window.localStorage.setItem(userKey, JSON.stringify(this.user));
    },
    logout() {
      this.token = "";
      this.user = null;
      window.localStorage.removeItem(tokenKey);
      window.localStorage.removeItem(userKey);
    },
  },
});
