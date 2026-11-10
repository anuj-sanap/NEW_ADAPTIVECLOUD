// frontend/src/pages/LoginPage.tsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { useAuthStore } from '@/store/authStore'

export default function LoginPage() {
  const navigate = useNavigate()
  const { setTokens, setUser } = useAuthStore()
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('password123')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const { data } = await axios.post('/api/v1/auth/login', { username, password })
      setTokens(data.access_token, data.refresh_token)

      // Decode role from JWT payload (base64)
      const payload = JSON.parse(atob(data.access_token.split('.')[1]))
      setUser(username, payload.role as string)
      navigate('/')
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        setError(err.response?.data?.detail ?? 'Login failed')
      } else {
        setError('Unexpected error')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <div className="w-full max-w-sm space-y-8 bg-gray-900 p-8 rounded-2xl shadow-2xl border border-gray-800">
        <div>
          <h1 className="text-2xl font-bold text-white text-center tracking-tight">
            Adaptive Cloud Security
          </h1>
          <p className="mt-1 text-sm text-gray-400 text-center">Sign in to your account</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label htmlFor="username" className="block text-sm font-medium text-gray-300 mb-1">
              Username
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoComplete="username"
              className="w-full rounded-lg bg-gray-800 border border-gray-700 px-4 py-2.5
                         text-white placeholder-gray-500 focus:outline-none focus:ring-2
                         focus:ring-primary-500 focus:border-transparent text-sm"
              placeholder="admin"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-300 mb-1">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              className="w-full rounded-lg bg-gray-800 border border-gray-700 px-4 py-2.5
                         text-white placeholder-gray-500 focus:outline-none focus:ring-2
                         focus:ring-primary-500 focus:border-transparent text-sm"
              placeholder="••••••••"
            />
          </div>

          {error && (
            <p className="text-sm text-red-400 bg-red-950 border border-red-800 rounded-lg px-4 py-2">
              {error}
            </p>
          )}

          <div className="bg-indigo-950/60 border border-indigo-800/80 rounded-lg p-3 text-xs text-indigo-300 flex items-center justify-between">
            <div>
              <span className="font-semibold block text-indigo-200">Default Credentials</span>
              <span>admin / password123</span>
            </div>
            <button
              type="button"
              onClick={() => { setUsername('admin'); setPassword('password123'); }}
              className="text-xs bg-indigo-600 hover:bg-indigo-500 text-white px-2.5 py-1 rounded transition-colors"
            >
              Autofill
            </button>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 px-4 rounded-lg bg-indigo-600 hover:bg-indigo-500
                       text-white font-semibold text-sm transition-colors
                       disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  )
}

