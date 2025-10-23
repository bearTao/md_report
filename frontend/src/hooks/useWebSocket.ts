/**
 * WebSocket Hook for real-time report generation progress
 */
import { useEffect, useRef, useState } from 'react';

export interface WSEvent {
  type: 'task_started' | 'task_completed' | 'task_failed' | 
        'render_failed' |
        'variable_started' | 'variable_completed' | 'variable_failed' | 
        'variable_progress' | 'heartbeat';
  task_id: string;
  timestamp: string;
  error?: {
    code: string;
    message: string;
    details?: string;
  };
  [key: string]: any;
}

export interface UseWebSocketOptions {
  onMessage?: (event: WSEvent) => void;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
  reconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

export function useWebSocket(
  taskId: string | null,
  options: UseWebSocketOptions = {}
) {
  const {
    onMessage,
    onOpen,
    onClose,
    onError,
    reconnect = true,
    reconnectInterval = 3000,
    maxReconnectAttempts = 5
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [events, setEvents] = useState<WSEvent[]>([]);
  const [latestEvent, setLatestEvent] = useState<WSEvent | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const sendMessageRef = useRef<((message: any) => void) | null>(null);
  const clearEventsRef = useRef<(() => void) | null>(null);

  // Store callbacks in refs to avoid recreating them
  const onMessageRef = useRef(onMessage);
  const onOpenRef = useRef(onOpen);
  const onCloseRef = useRef(onClose);
  const onErrorRef = useRef(onError);

  useEffect(() => {
    onMessageRef.current = onMessage;
    onOpenRef.current = onOpen;
    onCloseRef.current = onClose;
    onErrorRef.current = onError;
  }, [onMessage, onOpen, onClose, onError]);

  // Main effect for WebSocket connection
  useEffect(() => {
    if (!taskId) return;

    let ws: WebSocket | null = null;
    let reconnectAttempts = 0;
    let reconnectTimeout: NodeJS.Timeout | undefined;
    let unmounted = false;

    const connect = () => {
      if (unmounted || !taskId) return;
      
      // Close existing connection
      if (ws) {
        ws.close();
      }

      // Determine WebSocket URL
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = import.meta.env.VITE_API_BASE_URL?.replace(/^https?:\/\//, '') || 
                   window.location.host.replace(':5173', ':8000');
      const wsUrl = `${protocol}//${host}/ws/report-generation/${taskId}`;

      console.log('[WebSocket] Connecting to:', wsUrl);
      
      ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[WebSocket] Connected');
        setIsConnected(true);
        reconnectAttempts = 0;
        onOpenRef.current?.();
      };

      ws.onmessage = (event) => {
        try {
          const data: WSEvent = JSON.parse(event.data);
          console.log('[WebSocket] Message:', data);
          
          setLatestEvent(data);
          setEvents(prev => [...prev, data]);
          onMessageRef.current?.(data);
        } catch (error) {
          console.error('[WebSocket] Failed to parse message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error);
        onErrorRef.current?.(error);
      };

      ws.onclose = () => {
        console.log('[WebSocket] Disconnected');
        setIsConnected(false);
        wsRef.current = null;
        onCloseRef.current?.();

        // Auto reconnect
        if (reconnect && reconnectAttempts < maxReconnectAttempts && !unmounted) {
          reconnectAttempts++;
          console.log(`[WebSocket] Reconnecting... (attempt ${reconnectAttempts}/${maxReconnectAttempts})`);
          
          reconnectTimeout = setTimeout(() => {
            connect();
          }, reconnectInterval);
        }
      };
    };

    connect();

    return () => {
      unmounted = true;
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
      }
      if (ws) {
        ws.close();
        ws = null;
      }
      wsRef.current = null;
      setIsConnected(false);
    };
  }, [taskId, reconnect, reconnectInterval, maxReconnectAttempts]);

  // Stable sendMessage function
  useEffect(() => {
    sendMessageRef.current = (message: any) => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(typeof message === 'string' ? message : JSON.stringify(message));
      } else {
        console.warn('[WebSocket] Cannot send message, not connected');
      }
    };
  }, []);

  // Stable clearEvents function
  useEffect(() => {
    clearEventsRef.current = () => {
      setEvents([]);
      setLatestEvent(null);
    };
  }, []);

  return {
    isConnected,
    events,
    latestEvent,
    sendMessage: (message: any) => sendMessageRef.current?.(message),
    clearEvents: () => clearEventsRef.current?.(),
  };
}

