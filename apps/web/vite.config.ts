import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

const proxyTarget = process.env.VITE_DEV_PROXY_TARGET ?? 'http://127.0.0.1:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    Components({
      dts: false,
      resolvers: [ElementPlusResolver({ importStyle: 'css' })],
    }),
  ],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return;
          if (id.includes('vue-router')) return 'router';
          if (id.includes('pinia')) return 'state';
          if (id.includes('axios')) return 'network';
          if (id.includes('/vue/')) return 'vue';
        },
      },
    },
  },
  server: {
    allowedHosts: ['ivanshang.com'],
    proxy: {
      '/api': {
        target: proxyTarget,
        changeOrigin: true,
      },
    },
  },
})
