import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      // เพิ่ม Proxy นี้เพื่อดึงข้อมูลฮั่วเซ่งเฮงโดยไม่ติด CORS
      '/hsh-api': {
        target: 'https://apicheckpricev3.huasengheng.com',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/hsh-api/, '')
      }
    }
  }
})