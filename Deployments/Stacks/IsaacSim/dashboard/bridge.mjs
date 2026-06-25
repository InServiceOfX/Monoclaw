/**
 * bridge.mjs — UDP + HTTP → WebSocket bridge + FSW command relay
 *
 * Receives:
 *   - FSW decisions from Jetson fsw_orin on UDP :55055
 *   - Polls Isaac Sim telemetry HTTP API at :8282
 * Broadcasts to browser WebSocket clients on :5174
 *
 * Commands from browser:
 *   WS message { type: 'command', data: { action: 'liftoff' } }
 *   → POST to Jetson fsw_orin :8083/command (FSW validation)
 *   → Jetson forwards to Isaac Sim :8282/starship/command
 */

import { createSocket } from 'dgram';
import { WebSocketServer } from 'ws';
import http from 'http';

const UDP_PORT    = 55055;
const WS_PORT     = 5174;
const ISAAC_URL   = 'http://localhost:8282/telemetry/latest';
const JETSON_IP   = process.env.JETSON_IP ?? '192.168.86.34';
const JETSON_CMD  = `http://${JETSON_IP}:8083/command`;
const POLL_HZ     = 10;

const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Access-Control-Allow-Origin': '*' });
  res.end('FSW Bridge OK');
});

const wss = new WebSocketServer({ server });
const clients = new Set();

wss.on('connection', (ws) => {
  clients.add(ws);
  console.log(`[bridge] client connected (${clients.size} total)`);
  ws.on('close', () => clients.delete(ws));

  // Receive commands from browser → relay to Jetson FSW
  ws.on('message', async (raw) => {
    try {
      const msg = JSON.parse(raw.toString());
      if (msg.type !== 'command') return;

      const action = msg.data?.action ?? 'unknown';
      console.log(`[bridge] command from browser: ${action}`);

      // Forward to Jetson fsw_orin for FSW validation + Isaac Sim relay
      const resp = await fetch(JETSON_CMD, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(msg.data),
        signal: AbortSignal.timeout(8000),
      });
      const result = await resp.json();
      console.log(`[bridge] Jetson FSW response: ${JSON.stringify(result)}`);

      // Ack back to browser
      if (ws.readyState === 1) {
        ws.send(JSON.stringify({ type: 'command_ack', data: result, action }));
      }
      // Broadcast command to all clients so other dashboards update
      broadcast('command_sent', { action, result });

    } catch (e) {
      console.error(`[bridge] command relay error: ${e.message}`);
      if (ws.readyState === 1) {
        ws.send(JSON.stringify({ type: 'command_ack', data: { status: 'error', reason: e.message }, action: 'unknown' }));
      }
    }
  });
});

function broadcast(type, data) {
  const msg = JSON.stringify({ type, data, ts: Date.now() });
  for (const c of clients) {
    if (c.readyState === 1) c.send(msg);
  }
}

// UDP listener for FSW decisions from Jetson
const udp = createSocket('udp4');
udp.bind(UDP_PORT, () => console.log(`[bridge] UDP listening :${UDP_PORT}`));
udp.on('message', (buf, rinfo) => {
  try {
    const decision = JSON.parse(buf.toString());
    decision._from = rinfo.address;
    broadcast('decision', decision);
    console.log(`[bridge] decision from ${rinfo.address}: ${decision.rule}`);
  } catch { /* ignore malformed */ }
});

// Poll Isaac Sim telemetry
async function pollTelemetry() {
  try {
    const res = await fetch(ISAAC_URL, { signal: AbortSignal.timeout(500) });
    if (res.ok) broadcast('telemetry', await res.json());
  } catch { /* Isaac Sim not ready */ }
}
setInterval(pollTelemetry, 1000 / POLL_HZ);

server.listen(WS_PORT, () => {
  console.log(`[bridge] WebSocket server on ws://localhost:${WS_PORT}`);
  console.log(`[bridge] Jetson cmd relay → ${JETSON_CMD}`);
});
