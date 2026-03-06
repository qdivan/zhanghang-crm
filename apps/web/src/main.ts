import { createApp } from "vue";
import ElementPlus from "element-plus";
import type { Language } from "element-plus/es/locale";
import zhCn from "element-plus/es/locale/lang/zh-cn";
import { createPinia } from "pinia";

import "element-plus/dist/index.css";
import "./style.css";
import App from "./App.vue";
import router from "./router";

const app = createApp(App);

app.use(createPinia());
app.use(router);
app.use(ElementPlus, { locale: zhCn as unknown as Language });

app.mount("#app");
