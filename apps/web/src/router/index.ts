import { createRouter, createWebHistory } from "vue-router";

import { useAuthStore } from "../stores/auth";
import AddressResourceView from "../views/AddressResourceView.vue";
import AdminUsersView from "../views/AdminUsersView.vue";
import AppLayout from "../layouts/AppLayout.vue";
import BillingView from "../views/BillingView.vue";
import CostView from "../views/CostView.vue";
import CustomerDetailView from "../views/CustomerDetailView.vue";
import CustomersView from "../views/CustomersView.vue";
import LeadDetailView from "../views/LeadDetailView.vue";
import LeadView from "../views/LeadView.vue";
import LoginView from "../views/LoginView.vue";
import type { UserRole } from "../types";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/login",
      name: "login",
      component: LoginView,
    },
    {
      path: "/",
      component: AppLayout,
      children: [
        {
          path: "",
          redirect: "/leads",
        },
        {
          path: "leads",
          name: "leads",
          component: LeadView,
        },
        {
          path: "leads/:id",
          name: "lead-detail",
          component: LeadDetailView,
        },
        {
          path: "customers",
          name: "customers",
          component: CustomersView,
        },
        {
          path: "customers/:id",
          name: "customer-detail",
          component: CustomerDetailView,
        },
        {
          path: "billing",
          name: "billing",
          component: BillingView,
        },
        {
          path: "address-resources",
          name: "address-resources",
          component: AddressResourceView,
        },
        {
          path: "costs",
          name: "costs",
          component: CostView,
        },
        {
          path: "admin/users",
          name: "admin-users",
          component: AdminUsersView,
          meta: {
            roles: ["OWNER", "ADMIN"] as UserRole[],
          },
        },
      ],
    },
  ],
});

router.beforeEach((to) => {
  const auth = useAuthStore();
  if (!auth.ready) {
    auth.hydrate();
  }

  if (to.path !== "/login" && !auth.isLoggedIn) {
    return "/login";
  }
  if (to.path === "/login" && auth.isLoggedIn) {
    return "/leads";
  }
  const roleLimit = to.meta.roles as UserRole[] | undefined;
  if (roleLimit && auth.user && !roleLimit.includes(auth.user.role)) {
    return "/leads";
  }
  return true;
});

export default router;
