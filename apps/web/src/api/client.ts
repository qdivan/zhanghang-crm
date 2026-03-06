import axios from "axios";

const baseURL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

const tokenKey = "daizhang_token";
const userKey = "daizhang_user";
let redirectedToLogin = false;

export const apiClient = axios.create({
  baseURL,
  timeout: 10000,
});

apiClient.interceptors.request.use((config) => {
  const token = window.localStorage.getItem(tokenKey);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    if (status === 401) {
      window.localStorage.removeItem(tokenKey);
      window.localStorage.removeItem(userKey);
      if (!redirectedToLogin && window.location.pathname !== "/login") {
        redirectedToLogin = true;
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  },
);
