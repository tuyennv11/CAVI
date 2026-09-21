import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg', 'apple-touch-icon.png'],
      manifest: {
        name: 'LIVI — Hệ thống quản lý',
        short_name: 'LIVI',
        description: 'Đối tác, đơn hàng, tồn kho, ký duyệt — quản lý xuyên suốt cho LIVI.',
        theme_color: '#d80118',
        background_color: '#f8f5f5',
        display: 'standalone',
        start_url: '/',
        lang: 'vi',
        icons: [
          { src: '/pwa-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: '/pwa-512x512.png', sizes: '512x512', type: 'image/png' },
          { src: '/pwa-512x512-maskable.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      // API calls always go live (JWT-authenticated business data) — never serve them from cache.
      // Only the app shell (JS/CSS/icons) is precached so the app installs and opens instantly;
      // opening offline without a prior successful load still fails, same as before this change.
      workbox: {
        navigateFallbackDenylist: [/^\/api\//, /^\/admin\//, /^\/media\//],
        runtimeCaching: [
          {
            urlPattern: ({ url }) => url.pathname.startsWith('/api/'),
            handler: 'NetworkOnly',
          },
        ],
      },
    }),
  ],
})
