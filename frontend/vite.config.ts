/// <reference types="vitest/config" />
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// 환경변수는 저장소 루트 .env 하나만 쓴다 (.env.example 참고).
// 브라우저에서는 VITE_ 로 시작하는 값만 읽히므로 비밀값을 VITE_ 로 만들지 않는다.
export default defineConfig({
  envDir: '..',
  plugins: [react(), tailwindcss()],
  test: {
    environment: 'node',
  },
})
