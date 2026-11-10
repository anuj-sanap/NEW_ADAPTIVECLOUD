// frontend/src/hooks/useLiveChannel.ts
import { useEffect, useRef, useState, useCallback } from 'react';
import { useAuthStore } from '../store/authStore';
import { LiveStreamEnvelope } from '../types';

export type ConnectionStatus = 'connected' | 'connecting' | 'disconnected';

export function useLiveChannel<T = any>(channelName?: string, onEvent?: (envelope: LiveStreamEnvelope<T>) => void) {
  const token = useAuthStore((s) => s.token);
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [lastEvent, setLastEvent] = useState<LiveStreamEnvelope<T> | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const backoffRef = useRef<number>(1000);

  const connect = useCallback(() => {
    if (!token) {
      setStatus('disconnected');
      return;
    }

    setStatus('connecting');

    // Build WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws/live?token=${encodeURIComponent(token)}`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setStatus('connected');
        backoffRef.current = 1000; // Reset backoff on success

        // Subscribe to channel if specified
        if (channelName) {
          ws.send(JSON.stringify({ action: 'subscribe', channel: channelName }));
        }
      };

      ws.onmessage = (event) => {
        try {
          const envelope: LiveStreamEnvelope<T> = JSON.parse(event.data);
          if (!channelName || envelope.channel === channelName || envelope.channel === 'all') {
            setLastEvent(envelope);
            onEvent?.(envelope);
          }
        } catch {
          // Ignore parse errors on raw pings
        }
      };

      ws.onclose = () => {
        setStatus('disconnected');
        // Exponential backoff reconnect
        const delay = Math.min(backoffRef.current, 10000);
        backoffRef.current = Math.min(backoffRef.current * 1.5, 10000);
        reconnectTimeoutRef.current = window.setTimeout(() => {
          connect();
        }, delay);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      setStatus('disconnected');
    }
  }, [token, channelName, onEvent]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  const send = useCallback((channel: string, msgType: string, data: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          channel,
          type: msgType,
          ts: new Date().toISOString(),
          data,
        })
      );
    }
  }, []);

  return { status, lastEvent, send };
}

