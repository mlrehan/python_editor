import { KernelOutput, KernelStatus } from '../types';

export type OutputHandler = (cellId: string, output: KernelOutput) => void;
export type StatusHandler = (status: KernelStatus) => void;
export type ExecutionCompleteHandler = (
  cellId: string,
  reply: { status: string; execution_count?: number; execution_time?: number }
) => void;
export type InputRequestHandler = (cellId: string, prompt: string, password: boolean) => void;
export type ServerErrorHandler = (message: string, code?: string) => void;

// Heartbeat keeps proxies (nginx, Cloudflare) from closing an idle socket and detects dead connections
const HEARTBEAT_INTERVAL_MS = 25000;
const HEARTBEAT_TIMEOUT_MS = 10000;
const RECONNECT_BASE_DELAY_MS = 1000;
const RECONNECT_MAX_DELAY_MS = 15000;

export class KernelWebSocketClient {
  private ws: WebSocket | null = null;
  private sessionId: string;
  private token: string;
  private onOutput: OutputHandler;
  private onStatus: StatusHandler;
  private onComplete: ExecutionCompleteHandler;
  private onInputRequest?: InputRequestHandler;
  private onServerError?: ServerErrorHandler;
  private isConnected = false;
  private closedByClient = false;
  private reconnectAttempts = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private pongDeadline: ReturnType<typeof setTimeout> | null = null;
  // Resolves the pending restart() once the server confirms the kernel restarted
  private restartWaiter: { resolve: () => void; reject: (err: Error) => void; timer: ReturnType<typeof setTimeout> } | null = null;

  constructor(
    sessionId: string,
    token: string,
    onOutput: OutputHandler,
    onStatus: StatusHandler,
    onComplete: ExecutionCompleteHandler,
    onInputRequest?: InputRequestHandler,
    onServerError?: ServerErrorHandler
  ) {
    this.sessionId = sessionId;
    this.token = token;
    this.onOutput = onOutput;
    this.onStatus = onStatus;
    this.onComplete = onComplete;
    this.onInputRequest = onInputRequest;
    this.onServerError = onServerError;
  }

  connect() {
    if (this.ws) {
      this.disconnect();
    }
    this.closedByClient = false;
    this.open();
  }

  private open() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws/kernels/${this.sessionId}?token=${encodeURIComponent(this.token)}`;

    this.onStatus('connecting');
    const ws = new WebSocket(wsUrl);
    this.ws = ws;

    ws.onopen = () => {
      this.isConnected = true;
      this.reconnectAttempts = 0;
      this.startHeartbeat();
      this.onStatus('idle');
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'output') {
          this.onOutput(msg.cell_id, {
            output_type: msg.output_type,
            name: msg.name,
            text: msg.text,
            data: msg.data,
            metadata: msg.metadata,
            execution_count: msg.execution_count,
            ename: msg.ename,
            evalue: msg.evalue,
            traceback: msg.traceback,
            wait: msg.wait,
            display_id: msg.display_id,
          });
        } else if (msg.type === 'execute_reply') {
          this.onComplete(msg.cell_id, {
            status: msg.status,
            execution_count: msg.execution_count,
            execution_time: msg.execution_time,
          });
        } else if (msg.type === 'input_request') {
          this.onInputRequest?.(msg.cell_id, msg.prompt ?? '', !!msg.password);
        } else if (msg.type === 'status') {
          this.onStatus(msg.execution_state === 'busy' ? 'busy' : 'idle');
        } else if (msg.type === 'restarted') {
          this.onStatus('idle');
          this.settleRestart();
        } else if (msg.type === 'pong') {
          this.clearPongDeadline();
        } else if (msg.type === 'error') {
          console.warn('Kernel WebSocket error message:', msg.message);
          if (msg.code === 'capacity') {
            // Server is full: retry at the slowest pace instead of hammering it
            this.reconnectAttempts = Math.max(this.reconnectAttempts, 4);
          }
          if (msg.message) this.onServerError?.(msg.message, msg.code);
          if (this.restartWaiter && /restart/i.test(msg.message ?? '')) this.settleRestart(new Error(msg.message));
        }
      } catch (err) {
        console.error('Error parsing WebSocket message:', err);
      }
    };

    ws.onerror = (err) => {
      console.warn('Kernel WebSocket error:', err);
    };

    ws.onclose = () => {
      // Ignore close events from a socket that has already been replaced
      if (this.ws !== ws) return;
      this.isConnected = false;
      this.ws = null;
      this.stopHeartbeat();
      this.settleRestart(new Error('Connection to the kernel was lost during restart'));
      this.onStatus('disconnected');
      if (!this.closedByClient) {
        this.scheduleReconnect();
      }
    };
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) return;
    const delay = Math.min(RECONNECT_MAX_DELAY_MS, RECONNECT_BASE_DELAY_MS * 2 ** this.reconnectAttempts);
    this.reconnectAttempts += 1;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      if (!this.closedByClient) this.open();
    }, delay);
  }

  private startHeartbeat() {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
      this.ws.send(JSON.stringify({ type: 'ping' }));
      if (!this.pongDeadline) {
        // No pong in time: the connection is dead even if the browser has not noticed; force a reconnect
        this.pongDeadline = setTimeout(() => {
          this.pongDeadline = null;
          this.ws?.close();
        }, HEARTBEAT_TIMEOUT_MS);
      }
    }, HEARTBEAT_INTERVAL_MS);
  }

  private clearPongDeadline() {
    if (this.pongDeadline) {
      clearTimeout(this.pongDeadline);
      this.pongDeadline = null;
    }
  }

  private stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
    this.clearPongDeadline();
  }

  isOpen(): boolean {
    return this.isConnected && this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  // Resolves true once the socket is open, or false after timeoutMs (or if the client was closed)
  waitUntilOpen(timeoutMs: number): Promise<boolean> {
    return new Promise((resolve) => {
      const started = Date.now();
      const check = () => {
        if (this.isOpen()) return resolve(true);
        if (this.closedByClient || Date.now() - started >= timeoutMs) return resolve(false);
        setTimeout(check, 100);
      };
      check();
    });
  }

  execute(cellId: string, code: string) {
    if (!this.isOpen() || !this.ws) {
      throw new Error('WebSocket is not connected');
    }
    this.ws.send(
      JSON.stringify({
        type: 'execute',
        cell_id: cellId,
        code,
      })
    );
  }

  sendInput(value: string) {
    if (!this.isOpen() || !this.ws) {
      throw new Error('WebSocket is not connected');
    }
    this.ws.send(JSON.stringify({ type: 'input_reply', value }));
  }

  interrupt() {
    if (this.ws && this.isConnected) {
      this.ws.send(JSON.stringify({ type: 'interrupt' }));
    }
  }

  /**
   * Restarts the kernel over the socket. The server first drops queued executions (they get an
   * "abort" reply) so nothing from before the restart runs on the fresh kernel. Resolves when the
   * server confirms the restart.
   */
  restart(timeoutMs = 90000): Promise<void> {
    if (!this.isOpen() || !this.ws) {
      return Promise.reject(new Error('WebSocket is not connected'));
    }
    this.settleRestart(new Error('Superseded by a new restart request'));
    return new Promise<void>((resolve, reject) => {
      const timer = setTimeout(() => {
        this.restartWaiter = null;
        reject(new Error('The kernel did not confirm the restart in time'));
      }, timeoutMs);
      this.restartWaiter = { resolve, reject, timer };
      this.ws!.send(JSON.stringify({ type: 'restart' }));
    });
  }

  private settleRestart(error?: Error) {
    const waiter = this.restartWaiter;
    if (!waiter) return;
    this.restartWaiter = null;
    clearTimeout(waiter.timer);
    if (error) waiter.reject(error);
    else waiter.resolve();
  }

  disconnect() {
    this.closedByClient = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.stopHeartbeat();
    const ws = this.ws;
    this.ws = null;
    this.isConnected = false;
    ws?.close();
    this.settleRestart(new Error('Connection to the kernel was closed'));
    this.onStatus('disconnected');
  }
}
