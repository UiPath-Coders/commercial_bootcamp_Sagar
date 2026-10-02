import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { uipathCodedApps } from '@uipath/coded-apps-dev/vite';
import { resolve } from 'path';

// `base: './'` is mandatory for UiPath Coded Apps: the platform mounts the app
// under a non-root prefix, so every asset reference must be relative.
// `uipathCodedApps()` injects the <meta name="uipath:*"> tags from uipath.json
// during local dev; the platform injects the same tags in production.
export default defineConfig({
  plugins: [react(), uipathCodedApps()],
  base: './',
  optimizeDeps: {
    include: ['@uipath/uipath-typescript'],
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/react') || id.includes('node_modules/react-dom')) return 'vendor-react';
          if (id.includes('node_modules/@uipath')) return 'vendor-uipath';
          if (id.includes('node_modules/lucide-react')) return 'vendor-icons';
        },
      },
    },
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
    },
  },
});
