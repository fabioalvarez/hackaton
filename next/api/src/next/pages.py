"""The pages of the service: home, orders and health.

Each one is a single self-contained HTML document: the CSS and the JavaScript are inside, and it loads
nothing from outside (CT-02). The data of the pages comes from the JSON of the API itself.
"""

from html import escape

LAYOUT = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__ · Nodo Ruta</title>
<style>
  :root { --bg: #f4f6fb; --card: #fff; --text: #1b1f24; --muted: #5a626e; --line: #e3e7ee;
          --brand: #3b6cf6; --ok: #1a9d5b; --bad: #d83a3a; --warn: #c58a0b; --chip: #eef2ff; }
  @media (prefers-color-scheme: dark) {
    :root { --bg: #0f1420; --card: #171e2d; --text: #e8ecf4; --muted: #98a2b5; --line: #263046; --chip: #1e2a4a; } }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--text);
         font: 16px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
  main { max-width: 900px; margin: 0 auto; padding: 24px 20px 48px; }
  header { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; margin-bottom: 28px; }
  .brand { display: flex; align-items: center; gap: 12px; text-decoration: none; color: var(--text); }
  .brand span:last-child { display: grid; line-height: 1.2; } .brand small { color: var(--muted); }
  .logo { width: 44px; height: 44px; border-radius: 12px; background: linear-gradient(135deg, #3b6cf6, #7c4dff);
          display: grid; place-items: center; font-size: 22px; }
  nav { margin-left: auto; display: flex; gap: 6px; flex-wrap: wrap; }
  nav a { padding: 7px 14px; border-radius: 999px; text-decoration: none; color: var(--muted); font-weight: 600; font-size: 15px; }
  nav a:hover { background: var(--chip); } nav a.active { background: var(--brand); color: #fff; }
  h1 { margin: 0 0 6px; font-size: 30px; letter-spacing: -.5px; }
  .lead { font-size: 18px; color: var(--muted); margin: 0 0 4px; } .muted { color: var(--muted); }
  .hero { text-align: center; padding: 28px 0 34px; }
  .tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 16px; }
  .tile { background: var(--card); border: 1px solid var(--line); border-radius: 18px; padding: 22px; text-decoration: none;
          color: var(--text); transition: transform .15s, box-shadow .15s; }
  .tile:hover { transform: translateY(-3px); box-shadow: 0 10px 24px rgba(59, 108, 246, .15); }
  .tile .icon { font-size: 30px; } .tile h2 { margin: 8px 0 4px; font-size: 20px; } .tile p { margin: 0; color: var(--muted); }
  .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px; margin-bottom: 20px; }
  .card, section { background: var(--card); border: 1px solid var(--line); border-radius: 16px; padding: 16px 18px; }
  section { padding: 18px 20px; margin-bottom: 20px; }
  .card h2, section h2 { margin: 0 0 6px; font-size: 12px; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); }
  .value { font-size: 24px; font-weight: 700; word-break: break-word; }
  table { width: 100%; border-collapse: collapse; }
  th { text-align: left; font-size: 12px; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); }
  th, td { padding: 10px 8px; border-bottom: 1px solid var(--line); vertical-align: top; } tr:last-child td { border-bottom: 0; }
  td:first-child { white-space: nowrap; font-weight: 600; }
  .chip { padding: 3px 10px; border-radius: 999px; font-size: 13px; font-weight: 600; background: var(--chip); white-space: nowrap; }
  .delivered, .pass { background: #e3f6ec; color: var(--ok); } .in_transit { background: #e6eefe; color: var(--brand); }
  .preparing { background: #fff4d9; color: var(--warn); } .pending { background: #f0f1f4; color: var(--muted); }
  .fail { background: #fde8e8; color: var(--bad); }
  .big { display: flex; align-items: center; gap: 18px; }
  .dot { width: 64px; height: 64px; border-radius: 50%; background: var(--line); flex: none; }
  .dot.ok { background: var(--ok); box-shadow: 0 0 0 10px #1a9d5b22; } .dot.bad { background: var(--bad); box-shadow: 0 0 0 10px #d83a3a22; }
  .small { font-size: 14px; } code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
  footer { color: var(--muted); font-size: 14px; text-align: center; margin-top: 28px; }
  a { color: var(--brand); }
  .live { margin-top: 36px; background: var(--card); border: 1px solid var(--line); border-radius: 20px; padding: 22px 22px 18px;
          position: relative; overflow: hidden; }
  .live::before { content: ""; position: absolute; inset: 0 0 auto 0; height: 4px; background: var(--hue, var(--brand)); transition: background .4s; }
  .live h3, .live h4 { margin: 0; font-size: 12px; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); }
  .live h4 { margin: 22px 0 10px; display: flex; justify-content: space-between; align-items: baseline; gap: 10px; }
  .live h4 small { text-transform: none; letter-spacing: 0; font-weight: 400; }
  .live-top { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
  .live-top > div:first-child { display: grid; gap: 10px; }
  .server { display: inline-flex; align-items: center; gap: 14px; padding: 8px 18px 8px 12px; border-radius: 16px;
            background: var(--chip); border: 2px solid var(--hue, var(--brand)); transition: border-color .4s; }
  .server .led { width: 14px; height: 14px; border-radius: 50%; background: var(--hue, var(--brand)); animation: pulse 2s infinite; }
  .server .rack { font-size: 26px; }
  .server code { font-size: 20px; font-weight: 700; color: var(--hue, var(--brand)); }
  .server.down { border-color: var(--bad); } .server.down code { color: var(--bad); } .server.down .led { background: var(--bad); animation: none; }
  .server.swap { animation: pop .45s ease; }
  @keyframes pulse { 0% { box-shadow: 0 0 0 0 color-mix(in srgb, var(--hue, var(--brand)) 60%, transparent); } 70%, 100% { box-shadow: 0 0 0 10px transparent; } }
  @keyframes pop { 0% { transform: scale(.85) rotateX(60deg); opacity: .2; } 60% { transform: scale(1.06); } 100% { transform: none; opacity: 1; } }
  .controls { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
  .btn { border: 1px solid var(--line); background: var(--card); color: var(--text); padding: 8px 14px; border-radius: 999px;
         font: inherit; font-size: 14px; font-weight: 600; cursor: pointer; transition: transform .15s, box-shadow .15s; }
  .btn:hover { transform: translateY(-1px); box-shadow: 0 6px 16px rgba(59, 108, 246, .18); }
  .btn.primary { border: 0; color: #fff; background: linear-gradient(135deg, #3b6cf6, #7c4dff); }
  .btn.on { border-color: transparent; color: #fff; background: var(--ok); }
  .btn:disabled { opacity: .6; cursor: progress; transform: none; }
  select.btn { padding-right: 10px; }
  .kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px; margin-top: 18px; }
  .kpi { background: var(--bg); border-radius: 14px; padding: 10px 14px; }
  .kpi b { display: block; font-size: 22px; } .kpi span { font-size: 12px; color: var(--muted); }
  .live table { font-size: 14px; } .live th, .live td { padding: 7px 8px; } .live td:first-child { font-weight: 400; }
  .mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 13px; }
  .swatch { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 8px; vertical-align: middle; }
  .bar { height: 8px; min-width: 70px; background: var(--line); border-radius: 99px; overflow: hidden; }
  .bar span { display: block; height: 100%; transition: width .3s; }
  .warn { background: #fff4d9; color: var(--warn); } .info { background: var(--chip); color: var(--brand); }
  .feed { list-style: none; margin: 0; padding: 0; max-height: 260px; overflow: auto; }
  .feed li { display: grid; grid-template-columns: 70px 1fr; gap: 10px; padding: 7px 4px; border-bottom: 1px solid var(--line); font-size: 14px; }
  .feed li:last-child { border-bottom: 0; } .feed time { color: var(--muted); font-size: 12px; padding-top: 2px; }
  .feed li.bad { color: var(--bad); } .feed li.ok { color: var(--ok); } .feed li.warn, .feed li.info { background: none; }
  .scroll { max-height: 320px; overflow: auto; }
  .empty { color: var(--muted); font-size: 14px; padding: 6px 4px; }
</style>
</head>
<body>
<main>
  <header>
    <a class="brand" href="/"><span class="logo">&#128666;</span><span><b>Nodo Ruta</b><small>__SERVICE__</small></span></a>
    <nav>__NAV__</nav>
  </header>
  __BODY__
  <div class="live" id="live">
    <div class="live-top">
      <div>
        <h3>Instance serving you</h3>
        <div class="server" id="server"><span class="rack">&#128421;</span><span class="led"></span><code id="instance-id">__INSTANCE__</code></div>
      </div>
      <div class="controls">
        <select class="btn" id="path" title="Address to ask">
          <option value="/health">GET /health</option>
          <option value="/orders">GET /orders</option>
        </select>
        <button class="btn primary" id="switch" type="button">&#128260; One request</button>
        <button class="btn" id="burst" type="button">&#9889; 10 requests</button>
        <button class="btn" id="auto" type="button">&#9654; Live</button>
        <button class="btn" id="reset" type="button">Clear</button>
      </div>
    </div>
    <div class="kpis">
      <div class="kpi"><b id="k-total">0</b><span>requests</span></div>
      <div class="kpi"><b id="k-ok">-</b><span>answered OK</span></div>
      <div class="kpi"><b id="k-ms">-</b><span>average latency</span></div>
      <div class="kpi"><b id="k-version">-</b><span id="k-version-note">data version</span></div>
      <div class="kpi"><b id="k-inst">0</b><span>instances answering</span></div>
    </div>
    <h4>Instances <small>round robin: each one should get about the same share</small></h4>
    <table>
      <thead><tr><th>Instance</th><th>Requests</th><th>Share</th><th>Avg</th><th>Last answer</th><th>State</th></tr></thead>
      <tbody id="instances"></tbody>
    </table>
    <h4>What happened <small>changes the page detected, newest first</small></h4>
    <ul class="feed" id="events"></ul>
    <h4>Requests <small id="log-note">last 30, newest first</small></h4>
    <div class="scroll">
      <table>
        <thead><tr><th>Time</th><th>Request</th><th>Status</th><th>Instance</th><th>Data version</th><th>Time taken</th></tr></thead>
        <tbody id="log"></tbody>
      </table>
    </div>
  </div>
</main>
<script>
  const el = id => document.getElementById(id);
  let monitor = null;   // set by the live panel: it records every request the page makes
  async function getJson(path) {
    const t = Date.now(), start = performance.now();
    const entry = status => ({ t, path, status, ms: Math.round(performance.now() - start), id: '', version: '' });
    let response;
    try {
      response = await fetch(path, { headers: { Accept: 'application/json' }, cache: 'no-store' });
    } catch (error) {
      if (monitor) monitor(entry(0));
      throw error;
    }
    if (monitor) monitor(Object.assign(entry(response.status), {
      id: response.headers.get('x-instance-id') || '', version: response.headers.get('x-data-version') || '' }));
    return response;
  }
  function cell(row, text) { row.insertCell().textContent = text; }
  function chip(text, kind) {
    const span = document.createElement('span');
    span.className = 'chip ' + kind;
    span.textContent = text;
    return span;
  }
__SCRIPT__
  // Live panel: every request the page makes (its own, the buttons, the Live mode) is recorded here.
  // It is kept in sessionStorage, so the history survives moving between Home, Orders and Health.
  (function () {
    const KEY = 'nodo-ruta-live', MAX_LOG = 30, MAX_EVENTS = 50, LIVE_MS = 1000;
    const hueOf = id => { let h = 0; for (const c of id) h = (h * 31 + c.charCodeAt(0)) % 360; return h; };
    const colorOf = id => 'hsl(' + hueOf(id) + ' 70% 48%)';
    const clock = t => new Date(t).toLocaleTimeString([], { hour12: false });
    const ago = t => { const s = Math.round((Date.now() - t) / 1000); return s < 60 ? s + ' s ago' : Math.round(s / 60) + ' min ago'; };
    const fresh = () => ({ log: [], events: [], inst: {}, total: 0, ok: 0, msSum: 0, version: null, versionChanges: 0, failStreak: 0, live: false });
    let state;
    try { state = JSON.parse(sessionStorage.getItem(KEY)) || fresh(); } catch (error) { state = fresh(); }
    const save = () => { try { sessionStorage.setItem(KEY, JSON.stringify(state)); } catch (error) { /* private mode */ } };

    function note(kind, text) {
      state.events.unshift({ t: Date.now(), kind, text });
      state.events = state.events.slice(0, MAX_EVENTS);
    }

    function record(r) {
      const good = r.status >= 200 && r.status < 400;
      state.total++; state.msSum += r.ms; if (good) state.ok++;
      state.log.unshift(r); state.log = state.log.slice(0, MAX_LOG);

      // The service as a whole: down and back up.
      if (!good && state.failStreak === 0) {
        note('bad', r.status === 0 ? 'The service does not answer (no connection to the load balancer).'
          : r.id ? 'Instance ' + r.id + ' answered ' + r.status + ' on ' + r.path + (r.status === 503 ? ': it cannot read its data file.' : '.')
          : 'The load balancer answered ' + r.status + ' without any instance: none is available.');
      }
      if (good && state.failStreak > 0) note('ok', 'The service answers again after ' + state.failStreak + ' failed request' + (state.failStreak === 1 ? '' : 's') + '.');
      state.failStreak = good ? 0 : state.failStreak + 1;

      // Instances: new ones, ones that stop answering and come back.
      if (r.id) {
        let inst = state.inst[r.id];
        if (!inst) {
          inst = state.inst[r.id] = { n: 0, ok: 0, msSum: 0, first: r.t, last: r.t, status: r.status, gap: 0, missing: false };
          // The first few requests only discover the instances that already run; later, a new one is a new container.
          const discovering = state.total <= 6;
          note(discovering ? 'info' : 'warn', discovering
               ? 'Instance ' + r.id + ' answers' + (Object.keys(state.inst).length === 1 ? ' (first one seen).' : ': the load balancer spreads the requests.')
               : 'New instance ' + r.id + ' joined the rotation (a new container: deploy or restart).');
        }
        if (inst.missing) note('ok', 'Instance ' + r.id + ' answers again.');
        if (good && inst.status >= 400) note('ok', 'Instance ' + r.id + ' recovered: it answers ' + r.status + ' again.');
        inst.n++; inst.msSum += r.ms; inst.last = r.t; inst.status = r.status; inst.gap = 0; inst.missing = false;
        if (good) inst.ok++;

        // With round robin every answering instance shows up every few requests.
        const answering = Object.values(state.inst).filter(i => !i.missing).length;
        for (const [id, other] of Object.entries(state.inst)) {
          if (id === r.id || other.missing) continue;
          other.gap++;
          if (other.gap >= answering * 2 + 1) {
            other.missing = true;
            note('bad', 'Instance ' + id + ' did not answer the last ' + other.gap + ' requests: the load balancer took it out of rotation (stopped or unhealthy).');
          }
        }
      }

      // The data: a new version (a new file, or the backup restoring one).
      if (r.version) {
        if (state.version && r.version !== state.version) {
          state.versionChanges++;
          note('warn', 'The data version changed: ' + state.version + ' → ' + r.version + ' (new data, or the backup restored it).');
        }
        state.version = r.version;
      }
      save(); render();
    }

    function cells(row, values) { values.forEach(v => { const c = row.insertCell(); if (v instanceof Node) c.append(v); else c.textContent = v; }); }
    function instanceTag(id) {
      const span = document.createElement('span'); span.className = 'mono';
      if (!id) { span.textContent = '-'; return span; }
      const dot = document.createElement('span'); dot.className = 'swatch'; dot.style.background = colorOf(id);
      span.append(dot, id); return span;
    }
    const statusChip = s => chip(s === 0 ? 'no answer' : String(s), s >= 200 && s < 400 ? 'pass' : 'fail');
    const empty = (tbody, cols, text) => {
      const row = tbody.insertRow(), c = row.insertCell(); c.colSpan = cols; c.className = 'empty'; c.textContent = text;
    };

    const server = el('server');
    let shown = el('instance-id').textContent;
    function render() {
      const last = state.log[0];
      const current = last ? last.id : shown;
      if (current !== shown || (last && !last.id)) {
        server.classList.remove('swap'); void server.offsetWidth; server.classList.add('swap');
      }
      shown = current;
      server.classList.toggle('down', Boolean(last && !last.id));
      el('instance-id').textContent = last && !last.id ? 'none' : current;
      if (current) el('live').style.setProperty('--hue', colorOf(current));

      const ids = Object.keys(state.inst), answering = ids.filter(id => !state.inst[id].missing);
      el('k-total').textContent = state.total;
      el('k-ok').textContent = state.total ? Math.round(100 * state.ok / state.total) + '%' : '-';
      el('k-ms').textContent = state.total ? Math.round(state.msSum / state.total) + ' ms' : '-';
      el('k-version').textContent = state.version || '-';
      el('k-version-note').textContent = 'data version' + (state.versionChanges ? ' · changed ' + state.versionChanges + 'x' : '');
      el('k-inst').textContent = answering.length + (ids.length > answering.length ? ' / ' + ids.length : '');

      const tbody = el('instances'); tbody.replaceChildren();
      const seen = ids.reduce((sum, id) => sum + state.inst[id].n, 0);
      ids.forEach(id => {
        const i = state.inst[id], share = seen ? Math.round(100 * i.n / seen) : 0;
        const bar = document.createElement('div'); bar.className = 'bar';
        const fill = document.createElement('span'); fill.style.width = share + '%'; fill.style.background = colorOf(id); bar.append(fill);
        const wrap = document.createElement('div'); wrap.style.display = 'flex'; wrap.style.alignItems = 'center'; wrap.style.gap = '8px';
        wrap.append(bar, share + '%');
        const lastAnswer = document.createElement('span'); lastAnswer.append(statusChip(i.status), ' ' + ago(i.last));
        const st = i.missing ? chip('not answering', 'fail') : i.status >= 400 ? chip('answers with errors', 'warn') : chip('in rotation', 'pass');
        cells(tbody.insertRow(), [instanceTag(id), i.n, wrap, Math.round(i.msSum / i.n) + ' ms', lastAnswer, st]);
      });
      if (!ids.length) empty(tbody, 6, 'No instance has answered yet.');

      const feed = el('events'); feed.replaceChildren();
      state.events.forEach(e => {
        const li = document.createElement('li'); li.className = e.kind;
        const time = document.createElement('time'); time.textContent = clock(e.t);
        const text = document.createElement('span'); text.textContent = e.text;
        li.append(time, text); feed.append(li);
      });
      if (!state.events.length) feed.append(Object.assign(document.createElement('li'), { className: 'empty', textContent: 'Nothing yet. Press Live, then try make kill-instance, make corrupt or make deploy.' }));

      const log = el('log'); log.replaceChildren();
      state.log.forEach(r => {
        cells(log.insertRow(), [clock(r.t), 'GET ' + r.path, statusChip(r.status), instanceTag(r.id), r.version || '-', r.ms + ' ms']);
      });
      if (!state.log.length) empty(log, 6, 'No requests yet.');
    }

    // Every getJson of the pages goes through here, so their requests show up too.
    monitor = record;

    // The page itself was a request: record which instance served it.
    const nav = performance.getEntriesByType('navigation')[0];
    record({ t: Date.now(), path: location.pathname + ' (this page)', status: 200, id: shown,
             version: '', ms: nav ? Math.round(nav.responseEnd - nav.requestStart) : 0 });

    const busy = on => ['switch', 'burst'].forEach(id => { el(id).disabled = on; });
    async function one() { try { await getJson(el('path').value); } catch (error) { /* already recorded */ } }
    el('switch').addEventListener('click', async () => { busy(true); await one(); busy(false); });
    el('burst').addEventListener('click', async () => { busy(true); for (let i = 0; i < 10; i++) await one(); busy(false); });
    el('reset').addEventListener('click', () => { const live = state.live; state = fresh(); state.live = live; save(); render(); });

    let timer = null, inFlight = false;
    function setLive(on) {
      state.live = on; save();
      el('auto').classList.toggle('on', on);
      el('auto').textContent = on ? '⏸ Live: on' : '▶ Live';
      clearInterval(timer); timer = null;
      if (on) timer = setInterval(async () => { if (inFlight) return; inFlight = true; await one(); inFlight = false; }, LIVE_MS);
    }
    el('auto').addEventListener('click', () => setLive(!state.live));
    setLive(state.live);
    setInterval(render, 1000);   // keeps the "x s ago" fresh
  })();
</script>
</body>
</html>
"""

HOME = ("""
  <div class="hero">
    <h1>Nodo Ruta</h1>
    <p class="lead">Delivery status query service</p>
    <p class="muted">You are in the right place: <b>__SERVICE__</b></p>
  </div>
  <div class="tiles">
    <a class="tile" href="/orders"><div class="icon">&#128230;</div><h2>Orders</h2><p>The list of orders and the version of the data.</p></a>
    <a class="tile" href="/health"><div class="icon">&#128154;</div><h2>Health</h2><p>Whether the service is available.</p></a>
  </div>
""", "")

ORDERS = ("""
  <div class="cards">
    <div class="card"><h2>Data version</h2><div class="value" id="version">-</div></div>
    <div class="card"><h2>Orders</h2><div class="value" id="count">-</div></div>
  </div>
  <section>
    <h2>Orders</h2>
    <table>
      <thead><tr><th>Order</th><th>Zone</th><th>Status</th></tr></thead>
      <tbody id="orders"><tr><td colspan="3">Loading...</td></tr></tbody>
    </table>
    <p class="muted small">Programs get the same data as JSON from this same address.</p>
  </section>
""", """
  async function load() {
    const response = await getJson('/orders');
    if (!response.ok) {
      el('orders').replaceChildren(Object.assign(document.createElement('tr'), { innerHTML: '<td colspan="3">The data cannot be read right now.</td>' }));
      return;
    }
    const data = await response.json();
    el('version').textContent = response.headers.get('x-data-version');
    el('count').textContent = data.orders.length;
    el('orders').replaceChildren(...data.orders.map(order => {
      const row = document.createElement('tr');
      cell(row, order.id); cell(row, order.zone);
      row.insertCell().append(chip(order.status.replace('_', ' '), order.status));
      return row;
    }));
  }
  load().catch(() => el('orders').replaceChildren(Object.assign(document.createElement('tr'), { innerHTML: '<td colspan="3">The service does not answer right now.</td>' })));
""")

HEALTH = ("""
  <section>
    <div class="big">
      <div class="dot" id="dot"></div>
      <div><div class="value" id="state">Checking...</div><div class="muted" id="detail"></div></div>
    </div>
    <p class="muted small">Checked again every 5 seconds. Programs get the same answer as JSON from this same address.</p>
  </section>
""", """
  async function check() {
    try {
      const response = await getJson('/health');
      const data = response.ok ? await response.json() : null;
      el('dot').className = 'dot ' + (data ? 'ok' : 'bad');
      el('state').textContent = data ? 'Operational' : 'Unavailable';
      el('detail').textContent = data ? 'Data version ' + response.headers.get('x-data-version') : 'The data cannot be read (status ' + response.status + ')';
    } catch (error) {
      el('dot').className = 'dot bad';
      el('state').textContent = 'Unavailable';
      el('detail').textContent = 'The service does not answer';
    }
  }
  check();
  setInterval(check, 5000);
""")

PAGES = {"home": ("Home", HOME), "orders": ("Orders", ORDERS), "health": ("Health", HEALTH)}
MENU = [("home", "/", "Home"), ("orders", "/orders", "Orders"), ("health", "/health", "Health")]


def render(page: str, service_name: str, instance_id: str) -> str:
    title, (body, script) = PAGES[page]
    nav = "".join(f'<a href="{path}"{" class=active" if key == page else ""}>{label}</a>' for key, path, label in MENU)
    service, instance = escape(service_name), escape(instance_id)

    return (LAYOUT.replace("__TITLE__", title).replace("__NAV__", nav).replace("__BODY__", body)
            .replace("__SCRIPT__", script).replace("__SERVICE__", service).replace("__INSTANCE__", instance))
