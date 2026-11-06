import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './app/App.tsx'
import './index.css'

const root = document.getElementById('root')
if (!root) throw new Error('#root 요소가 없습니다 (index.html 확인)')

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
