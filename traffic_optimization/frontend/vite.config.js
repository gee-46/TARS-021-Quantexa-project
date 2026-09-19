import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: '../frontend_dist', // relative to frontend folder
    emptyOutDir: true,
    rollupOptions: {
      input: './src/index.jsx',
    },
  },
});
