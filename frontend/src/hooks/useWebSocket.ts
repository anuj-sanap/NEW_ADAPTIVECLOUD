// frontend/src/hooks/useWebSocket.ts
// Hook that manages a WebSocket connection to /ws/live.
// Dispatches incoming envelopes to registered channel listeners.

import { useCallback, useEffect, useRef, useState } from 'react'
import type { WsChannel, WsEnvelope } from '@/types'
import { useAuthStore } from '@/store/authStore'

type ChannelListener<T = unknown> = (envelope: WsEnvelope<T>) => void

interface UseWebSocketOptions {
  /** Called when WS connection state changes */
  onStatusChange?: (connected: boolean) => void
}

export function useWebSocket(options?: UseWebSocketOptions) {
  const accessToken = useAuthStore((s) => s.accessToken)
  const wsRef = useRef<WebSocket | null>(null)
  const listenersRef = useRef<Map<WsChannel, Set<ChannelListener>>>(new Map())
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [connected, setConnected] = useState(false)

  const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''
  const wsBase = BASE_URL.replace(/^https/, 'wss').replace(/^http/, 'ws')

  const connect = useCallback(() => {
    if (!accessToken) return
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const url = `${wsBase}/ws/live?token=${encodeURIComponent(accessToken)}`
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
      options?.onStatusChange?.(true)
      // Keep-alive ping every 30s
      const ping = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }))
        }
      }, 30_000)
      ws.addEventListener('close', () => clearInterval(ping))
    }

    ws.onmessage = (ev) => {
      try {
        const envelope: WsEnvelope = JSON.parse(ev.data as string)
        const listeners = listenersRef.current.get(envelope.channel)
        if (listeners) {
          listeners.forEach((fn) => fn(envelope))
        }
      } catch {
        // Ignore malformed messages
      }
    }

    ws.onclose = () => {
      setConnected(false)
      options?.onStatusChange?.(false)
      // Reconnect with back-off (3s)
      reconnectTimer.current = setTimeout(() => connect(), 3_000)
    }

    ws.onerror = () => ws.close()
  }, [accessToken, wsBase])

  useEffect(() => {
    connect()
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect])

  /** Subscribe to a specific WebSocket channel */
  const subscribe = useCallback(<T>(channel: WsChannel, listener: ChannelListener<T>) => {
    if (!listenersRef.current.has(channel)) {
      listenersRef.current.set(channel, new Set())
    }
    listenersRef.current.get(channel)!.add(listener as ChannelListener)

    return () => {
      listenersRef.current.get(channel)?.delete(listener as ChannelListener)
    }
  }, [])

  return { connected, subscribe }
}

