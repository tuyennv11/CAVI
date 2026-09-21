import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { registerSW } from 'virtual:pwa-register'
import './index.css'
import App from './App.jsx'

// registerType: 'autoUpdate' tự skipWaiting + reload khi phát hiện bản mới, nhưng chỉ tự KIỂM TRA
// có bản mới hay không lúc tab vừa mở — tab mở cả buổi sẽ không bao giờ biết có bản mới. Chủ động
// hỏi lại server mỗi 5 phút để tab đang mở cũng tự cập nhật, không cần đóng tab/xoá cache thủ công.
registerSW({
  immediate: true,
  onRegisteredSW(swUrl, registration) {
    if (!registration) return
    setInterval(() => registration.update(), 5 * 60 * 1000)
  },
})

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
)
