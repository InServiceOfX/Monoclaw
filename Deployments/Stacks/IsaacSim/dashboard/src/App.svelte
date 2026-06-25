<script lang="ts">
  import { onMount, onDestroy } from 'svelte';

  type Telemetry = {
    seq: number; sim_time: number;
    x: number; y: number; z: number;
    qw: number; qx: number; qy: number; qz: number;
    vx: number; vy: number; vz: number;
    wx: number; wy: number; wz: number;
  };

  type Decision = {
    rule: string; reasoning: string; decision: string;
    llm_secs: number;
    telemetry: { altitude_m: number; vy_mps: number; att_err_deg: number; spin_rads: number };
    timestamp: number; jetson_seq: number; sim_time: number; _from?: string;
  };

  let ws: WebSocket | null = null;
  let connected = $state(false);
  let telemetry = $state<Telemetry | null>(null);
  let decisions = $state<Decision[]>([]);
  let activeAlert = $state<string | null>(null);
  let velocityHistory = $state<{ vz: number; z: number }[]>([]);
  let alertTimeout: ReturnType<typeof setTimeout>;
  let cmdPending = $state(false);
  let cmdLastAck = $state<string | null>(null);

  async function sendCommand(action: string, extra: Record<string, unknown> = {}) {
    if (!ws || ws.readyState !== 1 || cmdPending) return;
    cmdPending = true;
    cmdLastAck = null;
    ws.send(JSON.stringify({ type: 'command', data: { action, ...extra } }));
  }
  const MAX_HISTORY = 200;

  function connect() {
    ws = new WebSocket('ws://localhost:5174');
    ws.onopen = () => { connected = true; };
    ws.onclose = () => { connected = false; setTimeout(connect, 2000); };
    ws.onerror = () => ws?.close();
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === 'telemetry') {
          telemetry = msg.data;
          velocityHistory = [...velocityHistory.slice(-MAX_HISTORY + 1),
            { vz: msg.data.vz, z: msg.data.z }];
        } else if (msg.type === 'decision') {
          decisions = [msg.data as Decision, ...decisions.slice(0, 9)];
          activeAlert = msg.data.rule;
          clearTimeout(alertTimeout);
          alertTimeout = setTimeout(() => activeAlert = null, 8000);
        } else if (msg.type === 'command_ack') {
          cmdPending = false;
          cmdLastAck = `${msg.action}: ${msg.data?.status ?? '?'}`;
          setTimeout(() => cmdLastAck = null, 4000);
        }
      } catch {}
    };
  }

  onMount(connect);
  onDestroy(() => ws?.close());

  function attitudeDeg(qw: number) {
    return 2 * Math.acos(Math.min(1, Math.abs(qw))) * (180 / Math.PI);
  }

  function spinRate(wx: number, wy: number, wz: number) {
    return Math.sqrt(wx*wx + wy*wy + wz*wz);
  }

  // SVG velocity graph
  function makePolyline(history: { vz: number }[], w: number, h: number): string {
    if (history.length < 2) return '';
    const min = Math.min(...history.map(h => h.vz));
    const max = Math.max(...history.map(h => h.vz), 0.1);
    const range = max - min || 1;
    return history.map((p, i) => {
      const x = (i / (history.length - 1)) * w;
      const y = h - ((p.vz - min) / range) * h;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(' ');
  }

  // Attitude indicator arc
  function attArc(qw: number): string {
    const deg = attitudeDeg(qw);
    const r = 44;
    const sweep = Math.min(deg / 90, 1) * Math.PI;
    const x = 50 + r * Math.sin(sweep);
    const y = 50 - r * Math.cos(sweep);
    const large = sweep > Math.PI ? 1 : 0;
    return `M 50 6 A ${r} ${r} 0 ${large} 1 ${x.toFixed(2)} ${y.toFixed(2)}`;
  }
</script>

<main>
  <header>
    <div class="logo">
      <span class="logo-mark">▲</span>
      <div>
        <div class="logo-text">STARSHIP FSW MISSION CONTROL</div>
        <div class="logo-sub">JETSON ORIN NANO · QWEN3.5-2B · ISAAC SIM 4.5</div>
      </div>
    </div>
    <div class="conn">
      <span class="dot" class:live={connected}></span>
      <span class:live={connected}>{connected ? 'LIVE TELEMETRY' : 'CONNECTING…'}</span>
      <span class="seq">PKT #{(telemetry?.seq ?? 0).toLocaleString()}</span>
    </div>
  </header>

  {#if activeAlert}
    <div class="alert-banner" class:abort={activeAlert === 'ALTITUDE_ABORT'}
                              class:attitude={activeAlert === 'ATTITUDE_ANOMALY'}
                              class:spin={activeAlert === 'SPIN_ANOMALY'}>
      ⚡ FSW RULE: {activeAlert.replace('_', ' ')}
    </div>
  {/if}

  <!-- Command panel -->
  <div class="cmd-bar">
    <span class="cmd-label">FSW COMMAND</span>
    <button class="cmd-btn liftoff" onclick={() => sendCommand('liftoff', { velocity_y: 80 })}
      disabled={cmdPending}>
      ▲ LIFTOFF
    </button>
    <button class="cmd-btn abort" onclick={() => sendCommand('abort')}
      disabled={cmdPending}>
      ⬛ ABORT
    </button>
    <button class="cmd-btn reset" onclick={() => sendCommand('reset_position')}
      disabled={cmdPending}>
      ↺ RESET
    </button>
    {#if cmdPending}
      <span class="cmd-status pending">● Routing via Jetson FSW…</span>
    {:else if cmdLastAck}
      <span class="cmd-status ack">✓ {cmdLastAck}</span>
    {:else}
      <span class="cmd-route">DESKTOP → JETSON FSW :8083 → ISAAC SIM :8282</span>
    {/if}
  </div>

  <div class="grid">

    <!-- Gauges column -->
    <section class="gauges">
      <!-- Altitude -->
      <div class="gauge" class:danger={telemetry && telemetry.z < 5}>
        <div class="g-label">ALTITUDE</div>
        <div class="g-value" class:danger-val={telemetry && telemetry.z < 5}>
          {(telemetry?.z ?? 0).toFixed(1)}
        </div>
        <div class="g-unit">metres AGL</div>
        <div class="g-bar">
          <div class="g-fill"
            style="width:{Math.max(0, Math.min(100, ((telemetry?.z ?? 0) / 1000) * 100))}%"></div>
        </div>
      </div>

      <!-- Vertical velocity -->
      <div class="gauge" class:danger={telemetry && telemetry.vz < -2}>
        <div class="g-label">VERT VELOCITY</div>
        <div class="g-value" class:danger-val={telemetry && telemetry.vz < -2}>
          {(telemetry?.vz ?? 0).toFixed(2)}
        </div>
        <div class="g-unit">m/s</div>
        <div class="g-bar">
          <div class="g-fill vy"
            style="width:{Math.min(100, Math.abs(telemetry?.vz ?? 0) / 10 * 100)}%"></div>
        </div>
      </div>

      <!-- Attitude error -->
      {#if telemetry}
        {@const att = attitudeDeg(telemetry.qw)}
        <div class="gauge" class:danger={att > 45}>
          <div class="g-label">ATTITUDE ERR</div>
          <div class="g-value" class:danger-val={att > 45}>{att.toFixed(1)}</div>
          <div class="g-unit">degrees</div>
          <!-- SVG attitude arc -->
          <svg viewBox="0 0 100 55" class="att-arc">
            <circle cx="50" cy="50" r="44" fill="none" stroke="#0a2a4a" stroke-width="6"/>
            <path d={attArc(telemetry.qw)} fill="none"
              stroke={att > 45 ? '#f44' : att > 20 ? '#fa0' : '#4af'}
              stroke-width="6" stroke-linecap="round"/>
            <text x="50" y="48" text-anchor="middle" fill="#578" font-size="8">45°</text>
          </svg>
        </div>
      {/if}

      <!-- Spin rate -->
      {#if telemetry}
        {@const sp = spinRate(telemetry.wx, telemetry.wy, telemetry.wz)}
        <div class="gauge" class:danger={sp > 1}>
          <div class="g-label">SPIN RATE</div>
          <div class="g-value" class:danger-val={sp > 1}>{sp.toFixed(3)}</div>
          <div class="g-unit">rad/s</div>
          <div class="g-bar">
            <div class="g-fill spin" style="width:{Math.min(100, sp * 100)}%"></div>
          </div>
        </div>
      {/if}

      <!-- Sim time -->
      <div class="gauge sim-gauge">
        <div class="g-label">SIM TIME</div>
        <div class="g-value small">{(telemetry?.sim_time ?? 0).toFixed(3)}</div>
        <div class="g-unit">seconds</div>
      </div>
    </section>

    <!-- Center: velocity graph -->
    <section class="center">
      <div class="graph-title">VERTICAL VELOCITY HISTORY</div>
      <div class="graph-wrap">
        <svg class="graph" viewBox="0 0 600 180" preserveAspectRatio="none">
          <!-- Grid lines -->
          {#each [0,1,2,3,4] as i}
            <line x1="0" y1={i*45} x2="600" y2={i*45} stroke="#0a2a4a" stroke-width="0.5"/>
          {/each}
          <!-- Zero line -->
          <line x1="0" y1="90" x2="600" y2="90" stroke="#0a4a7a" stroke-width="1"/>
          <!-- Velocity polyline -->
          {#if velocityHistory.length > 1}
            <polyline
              points={makePolyline(velocityHistory, 600, 180)}
              fill="none" stroke="#4af" stroke-width="2"
              style="filter:drop-shadow(0 0 3px #4af)"
            />
          {/if}
          <!-- Danger threshold line -->
          <line x1="0" y1="135" x2="600" y2="135" stroke="#f443" stroke-width="1" stroke-dasharray="4,4"/>
          <text x="4" y="133" fill="#f44" font-size="8">-2 m/s abort</text>
        </svg>
      </div>

      <!-- Starship schematic / attitude -->
      <div class="schematic-wrap">
        <div class="schematic-title">VEHICLE ATTITUDE</div>
        {#if telemetry}
          {@const tiltDeg = attitudeDeg(telemetry.qw)}
          <svg viewBox="-30 -80 60 160" class="starship-svg">
            <g transform="rotate({tiltDeg.toFixed(1)})">
              <!-- Body -->
              <ellipse cx="0" cy="0" rx="6" ry="40" fill="#1a3a5a" stroke="#4af" stroke-width="0.8"/>
              <!-- Nose -->
              <ellipse cx="0" cy="-40" rx="6" ry="12" fill="#4af" opacity="0.8"/>
              <!-- Fins -->
              <polygon points="-6,25 -18,40 -6,35" fill="#0a2a4a" stroke="#4af" stroke-width="0.5"/>
              <polygon points="6,25 18,40 6,35" fill="#0a2a4a" stroke="#4af" stroke-width="0.5"/>
              <!-- Engine glow -->
              <ellipse cx="0" cy="42" rx="4" ry="3" fill="#ff6030" opacity="0.7"
                style="filter:blur(2px)"/>
            </g>
            <!-- Ground reference -->
            <line x1="-28" y1="72" x2="28" y2="72" stroke="#3a5a7a" stroke-width="0.8"
              stroke-dasharray="3,3"/>
            <text x="0" y="80" text-anchor="middle" fill="#3a5a7a" font-size="6">SURFACE</text>
          </svg>
        {/if}
      </div>
    </section>

    <!-- Right: FSW decisions -->
    <section class="decisions">
      <div class="decisions-header">
        <span>FSW AI UPLINK</span>
        <span class="from-label">← JETSON ORIN NANO</span>
      </div>
      {#each decisions as d, i (d.timestamp)}
        <div class="decision-card" class:latest={i === 0}
          class:abort={d.rule === 'ALTITUDE_ABORT'}
          class:attitude={d.rule === 'ATTITUDE_ANOMALY'}>
          <div class="card-header">
            <span class="card-rule">{d.rule.replace('_', ' ')}</span>
            <span class="card-time">{new Date(d.timestamp * 1000).toLocaleTimeString()}</span>
          </div>
          <div class="card-telem">
            ALT {d.telemetry.altitude_m.toFixed(1)}m
            VY {d.telemetry.vy_mps.toFixed(1)}m/s
            ATT {d.telemetry.att_err_deg.toFixed(1)}°
          </div>
          {#if d.reasoning}
            <div class="card-think">
              <span class="think-label">THINK</span>
              {d.reasoning.slice(0, 200)}{d.reasoning.length > 200 ? '…' : ''}
            </div>
          {/if}
          <div class="card-decision">
            <span class="dec-label">DECISION</span>
            <span class="dec-text">{d.decision || '(processing…)'}</span>
          </div>
          <div class="card-footer">
            {d.llm_secs.toFixed(1)}s · Qwen3.5-2B · {d._from ?? 'jetson'}
          </div>
        </div>
      {/each}
      {#if decisions.length === 0}
        <div class="no-decisions">
          <div class="waiting-dot"></div>
          Awaiting FSW decisions from Jetson Orin Nano…
        </div>
      {/if}
    </section>

  </div>
</main>

<style>
  :global(*, *::before, *::after) { box-sizing: border-box; margin: 0; padding: 0; }
  :global(body) {
    background: #030810;
    color: #a8c8e8;
    font-family: 'Courier New', Courier, monospace;
    height: 100vh;
    overflow: hidden;
    font-size: 13px;
  }

  main { display: flex; flex-direction: column; height: 100vh; }

  /* ── Header ── */
  header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 10px 20px;
    background: linear-gradient(90deg, #040c18, #061428);
    border-bottom: 1px solid #0c3c6a;
    flex-shrink: 0;
  }
  .logo { display: flex; align-items: center; gap: 14px; }
  .logo-mark { font-size: 2rem; color: #4af; text-shadow: 0 0 12px #4af; }
  .logo-text { font-size: 1rem; font-weight: bold; color: #7df; letter-spacing: 0.2em; }
  .logo-sub  { font-size: 0.55rem; color: #468; letter-spacing: 0.15em; margin-top: 2px; }
  .conn { display: flex; align-items: center; gap: 10px; font-size: 0.65rem; letter-spacing: 0.1em; }
  .dot { width: 8px; height: 8px; border-radius: 50%; background: #f44; flex-shrink: 0; }
  .dot.live { background: #0f8; box-shadow: 0 0 8px #0f8; animation: blink 1.8s infinite; }
  .conn .live { color: #0f8; }
  .seq { color: #468; margin-left: 12px; }

  @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.4} }

  /* ── Command bar ── */
  .cmd-bar {
    display: flex; align-items: center; gap: 10px;
    padding: 8px 20px;
    background: rgba(0,15,35,0.95);
    border-bottom: 1px solid #0c3c6a;
    flex-shrink: 0;
  }
  .cmd-label { font-size: 0.55rem; letter-spacing: 0.15em; color: #468; flex-shrink: 0; }
  .cmd-btn {
    padding: 5px 16px;
    border: 1px solid;
    border-radius: 3px;
    font-family: inherit;
    font-size: 0.7rem;
    font-weight: bold;
    letter-spacing: 0.1em;
    cursor: pointer;
    transition: all 0.15s;
    background: transparent;
  }
  .cmd-btn:disabled { opacity: 0.4; cursor: not-allowed; }
  .cmd-btn.liftoff { border-color: #0f8; color: #0f8; }
  .cmd-btn.liftoff:hover:not(:disabled) { background: rgba(0,255,128,0.12); box-shadow: 0 0 8px #0f84; }
  .cmd-btn.abort   { border-color: #f44; color: #f44; }
  .cmd-btn.abort:hover:not(:disabled)   { background: rgba(255,60,40,0.12);  box-shadow: 0 0 8px #f444; }
  .cmd-btn.reset   { border-color: #4af; color: #4af; }
  .cmd-btn.reset:hover:not(:disabled)   { background: rgba(64,170,255,0.12); box-shadow: 0 0 8px #4af4; }
  .cmd-status { font-size: 0.65rem; }
  .cmd-status.pending { color: #fa0; animation: blink 0.8s infinite; }
  .cmd-status.ack     { color: #0f8; }
  .cmd-route { font-size: 0.55rem; color: #2a4a6a; margin-left: auto; }

  /* ── Alert banner ── */
  .alert-banner {
    text-align: center;
    padding: 8px;
    font-size: 0.85rem;
    font-weight: bold;
    letter-spacing: 0.2em;
    animation: flash 0.5s ease-in-out infinite alternate;
    flex-shrink: 0;
  }
  .alert-banner.abort    { background: rgba(255,40,20,0.25); color: #f64; border-bottom: 1px solid #f644; }
  .alert-banner.attitude { background: rgba(255,160,0,0.2);  color: #fa6; border-bottom: 1px solid #fa64; }
  .alert-banner.spin     { background: rgba(255,220,0,0.15); color: #fd6; border-bottom: 1px solid #fd64; }
  @keyframes flash { from{opacity:0.7} to{opacity:1} }

  /* ── Main grid ── */
  .grid {
    display: grid;
    grid-template-columns: 200px 1fr 340px;
    flex: 1;
    overflow: hidden;
    gap: 1px;
    background: #0a1a2a;
  }

  /* ── Gauges ── */
  .gauges {
    display: flex; flex-direction: column; gap: 8px;
    padding: 14px 10px;
    background: #040c18;
    overflow-y: auto;
    border-right: 1px solid #0c3c6a;
  }

  .gauge {
    background: rgba(0,30,60,0.6);
    border: 1px solid #0a3a5a;
    border-radius: 4px;
    padding: 10px 12px;
    transition: border-color 0.2s, background 0.2s;
  }
  .gauge.danger {
    border-color: #f44;
    background: rgba(80,10,10,0.5);
    box-shadow: 0 0 12px rgba(255,50,30,0.3);
  }

  .g-label { font-size: 0.55rem; letter-spacing: 0.15em; color: #468; margin-bottom: 4px; }
  .g-value { font-size: 1.4rem; color: #4af; font-weight: bold; line-height: 1; }
  .g-value.small { font-size: 1rem; }
  .g-value.danger-val { color: #f64; text-shadow: 0 0 8px #f64; }
  .g-unit  { font-size: 0.55rem; color: #468; margin-bottom: 8px; }

  .g-bar { height: 4px; background: #0a2a4a; border-radius: 2px; overflow: hidden; }
  .g-fill { height: 100%; background: #4af; border-radius: 2px; transition: width 0.3s; }
  .g-fill.vy   { background: #f64; }
  .g-fill.spin { background: #fa0; }

  .att-arc { width: 100%; margin-top: 4px; }
  .sim-gauge .g-value { font-size: 0.9rem; color: #468; }

  /* ── Center ── */
  .center {
    display: flex; flex-direction: column;
    padding: 14px;
    background: #050d1a;
    gap: 10px;
    overflow: hidden;
  }

  .graph-title {
    font-size: 0.6rem; letter-spacing: 0.15em; color: #468;
    border-bottom: 1px solid #0a3a5a; padding-bottom: 6px;
  }

  .graph-wrap { flex: 1; min-height: 0; }
  .graph { width: 100%; height: 100%; }

  .schematic-wrap { display: flex; flex-direction: column; align-items: center; gap: 4px; }
  .schematic-title { font-size: 0.55rem; letter-spacing: 0.12em; color: #468; }
  .starship-svg { width: 80px; height: 160px; }

  /* ── Decisions ── */
  .decisions {
    background: #040c18;
    border-left: 1px solid #0c3c6a;
    display: flex; flex-direction: column;
    overflow: hidden;
  }

  .decisions-header {
    padding: 10px 14px;
    font-size: 0.6rem; letter-spacing: 0.15em; color: #4af;
    border-bottom: 1px solid #0c3c6a;
    display: flex; justify-content: space-between; align-items: center;
    flex-shrink: 0;
  }
  .from-label { color: #468; font-size: 0.55rem; }

  .decision-card {
    border-bottom: 1px solid #0a2a4a;
    padding: 10px 14px;
    transition: background 0.3s;
    overflow-y: auto;
    max-height: 200px;
  }
  .decision-card.latest { background: rgba(0,40,80,0.4); }
  .decision-card.abort   { border-left: 3px solid #f44; }
  .decision-card.attitude { border-left: 3px solid #fa0; }

  .card-header { display: flex; justify-content: space-between; margin-bottom: 4px; }
  .card-rule { font-size: 0.65rem; font-weight: bold; color: #f64; letter-spacing: 0.1em; }
  .card-time { font-size: 0.55rem; color: #468; }

  .card-telem { font-size: 0.6rem; color: #578; margin-bottom: 6px; }

  .card-think {
    background: rgba(0,20,50,0.5);
    border-left: 2px solid #0c3c6a;
    padding: 6px 8px;
    margin-bottom: 6px;
    font-size: 0.6rem; color: #578; line-height: 1.4;
  }
  .think-label {
    display: inline-block; font-size: 0.5rem; color: #4af; letter-spacing: 0.1em;
    border: 1px solid #0c3c6a; border-radius: 2px; padding: 0 4px; margin-right: 6px;
  }

  .card-decision { display: flex; flex-direction: column; gap: 3px; margin-bottom: 4px; }
  .dec-label { font-size: 0.5rem; color: #4af; letter-spacing: 0.1em; }
  .dec-text  { font-size: 0.72rem; color: #cef; line-height: 1.4; }

  .card-footer { font-size: 0.5rem; color: #468; }

  .no-decisions {
    display: flex; flex-direction: column; align-items: center; gap: 12px;
    padding: 30px 16px; color: #2a4a6a; font-size: 0.7rem;
    text-align: center;
  }

  .waiting-dot {
    width: 12px; height: 12px; border-radius: 50%;
    border: 2px solid #0c3c6a;
    border-top-color: #4af;
    animation: spin 1s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
