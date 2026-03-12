import { dirname, resolve } from 'path';
import { fileURLToPath } from 'url';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const __dirname = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(__dirname, '../..');

export default defineConfig({
  root: __dirname,
  plugins: [react()],
  build: {
    outDir: resolve(__dirname, '../ui'),
    emptyOutDir: false,
  },
  server: {
    proxy: {
      '/api': 'http://localhost:7878',
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    include: [
      `${__dirname}/**/*.test.{js,jsx}`,
      `${repoRoot}/tests/js/**/*.test.js`,
    ],
    exclude: [
      '**/node_modules/**',
      '**/.worktrees/**',
    ],
    setupFiles: [resolve(__dirname, 'test-setup.js')],
  },
});
