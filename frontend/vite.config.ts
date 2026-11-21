import { defineConfig, loadEnv, type ProxyOptions } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, fileURLToPath(new URL('.', import.meta.url)), [
    'SUPABASE_URL', 'SUPABASE_PUBLISHABLE_KEY', 'VITE_SUPABASE_', 'COLLECTIONS_API_URL', 'TRIGGER_API_KEY',
  ])
  // Same-origin /api for the collections API. The key stays on this server and calls are always dry runs.
  const isAllowed = (method = '', path = '') => (method === 'GET' && path === '/api/queue') || (method === 'POST' && path === '/api/trigger/call')
  const proxy: Record<string, ProxyOptions> = {
    '/api': {
      target: env.COLLECTIONS_API_URL || 'http://127.0.0.1:8000',
      headers: { 'X-API-Key': env.TRIGGER_API_KEY || '' },
      bypass: req => isAllowed(req.method, req.url?.split('?')[0]) ? undefined : false,
      rewrite: url => url.split('?')[0] === '/api/queue' ? '/queue' : '/trigger/call?dry_run=true',
    },
  }
  return {
    plugins: [react(), tailwindcss()],
    define: {
      'import.meta.env.VITE_SUPABASE_URL': JSON.stringify(env.SUPABASE_URL || env.VITE_SUPABASE_URL || ''),
      'import.meta.env.VITE_SUPABASE_ANON_KEY': JSON.stringify(env.SUPABASE_PUBLISHABLE_KEY || env.VITE_SUPABASE_ANON_KEY || ''),
    },
    server: { proxy },
    preview: { proxy },
    build: {
      rolldownOptions: { output: { manualChunks: (id) => id.includes('@supabase/') ? 'supabase' : undefined } },
    },
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
  }
})
