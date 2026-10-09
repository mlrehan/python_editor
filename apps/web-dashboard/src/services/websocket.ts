import { KernelOutput, KernelStatus } from '../types';

export type OutputHandler = (cellId: string, output: KernelOutput) => void;
export type StatusHandler = (status: KernelStatus) => void;
export type ExecutionCompleteHandler = (
  cellId: string,
  reply: { status: string; execution_count?: number; execution_time?: number }
) => void;

export class KernelWebSocketClient {
  private ws: WebSocket | null = null;
  private sessionId: string;
  private token: string;
  private onOutput: OutputHandler;
  private onStatus: StatusHandler;
  private onComplete: ExecutionCompleteHandler;
  private isConnected = false;

  constructor(
    sessionId: string,
    token: string,
    onOutput: OutputHandler,
    onStatus: StatusHandler,
    onComplete: ExecutionCompleteHandler
  ) {
    this.sessionId = sessionId;
    this.token = token;
    this.onOutput = onOutput;
    this.onStatus = onStatus;
    this.onComplete = onComplete;
  }

  connect() {
    if (this.ws) {
      this.disconnect();
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws/kernels/${this.sessionId}?token=${encodeURIComponent(this.token)}`;

    this.onStatus('connecting');
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      this.isConnected = true;
      this.onStatus('idle');
    };

    this.ws.onmessage = (event) => {
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
          });
        } else if (msg.type === 'execute_reply') {
          this.onComplete(msg.cell_id, {
            status: msg.status,
            execution_count: msg.execution_count,
            execution_time: msg.execution_time,
          });
        } else if (msg.type === 'status') {
          this.onStatus(msg.execution_state === 'busy' ? 'busy' : 'idle');
        } else if (msg.type === 'restarted') {
          this.onStatus('idle');
        }
      } catch (err) {
        console.error('Error parsing WebSocket message:', err);
      }
    };

    this.ws.onerror = (err) => {
      console.warn('Kernel WebSocket error:', err);
      this.onStatus('disconnected');
    };

    this.ws.onclose = () => {
      this.isConnected = false;
      this.onStatus('disconnected');
    };
  }

  execute(cellId: string, code: string) {
    if (!this.ws || !this.isConnected) {
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

  interrupt() {
    if (this.ws && this.isConnected) {
      this.ws.send(JSON.stringify({ type: 'interrupt' }));
    }
  }

  restart() {
    if (this.ws && this.isConnected) {
      this.ws.send(JSON.stringify({ type: 'restart' }));
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.isConnected = false;
    this.onStatus('disconnected');
  }
}

