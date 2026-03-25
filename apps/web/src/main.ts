import { createApp } from "vue";
import { ElLoadingDirective } from "element-plus";
import { createPinia } from "pinia";

import "./style.css";
import App from "./App.vue";
import router from "./router";

const app = createApp(App);

app.use(createPinia());
app.use(router);
app.directive("loading", ElLoadingDirective);

app.mount("#app");
