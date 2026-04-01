import { useAuthStore } from '@/store/authStore'
import { LoginForm } from '@/components/auth/LoginForm'
import { ChatWindow } from '@/components/chat/ChatWindow'

export default function App() {
  const user = useAuthStore((s) => s.user)
  return user ? <ChatWindow /> : <LoginForm />
}
