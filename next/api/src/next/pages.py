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
  .instance { margin: 40px auto 0; max-width: 560px; text-align: center; background: var(--card); border: 1px solid var(--line); border-radius: 20px;
              padding: 28px 24px 24px; position: relative; overflow: hidden; }
  .instance::before { content: ""; position: absolute; inset: 0 0 auto 0; height: 4px; background: var(--hue, var(--brand)); transition: background .4s; }
  .instance h3 { margin: 0 0 18px; font-size: 12px; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); }
  .server { display: inline-flex; align-items: center; gap: 14px; padding: 10px 20px 10px 12px; border-radius: 16px;
            background: var(--chip); border: 2px solid var(--hue, var(--brand)); transition: border-color .4s; }
  .server .led { width: 14px; height: 14px; border-radius: 50%; background: var(--hue, var(--brand)); box-shadow: 0 0 0 0 var(--hue, var(--brand)); animation: pulse 2s infinite; }
  .server .rack { font-size: 28px; }
  .server code { font-size: 20px; font-weight: 700; color: var(--hue, var(--brand)); }
  .server.swap { animation: pop .45s ease; }
  @keyframes pulse { 0% { box-shadow: 0 0 0 0 color-mix(in srgb, var(--hue, var(--brand)) 60%, transparent); } 70%, 100% { box-shadow: 0 0 0 10px transparent; } }
  @keyframes pop { 0% { transform: scale(.85) rotateX(60deg); opacity: .2; } 60% { transform: scale(1.06); } 100% { transform: none; opacity: 1; } }
  .switch { display: block; margin: 24px auto 0; border: 0; cursor: pointer; padding: 11px 24px; border-radius: 999px; font: inherit; font-weight: 700;
            color: #fff; background: linear-gradient(135deg, #3b6cf6, #7c4dff); transition: transform .15s, box-shadow .15s, opacity .15s; }
  .switch:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(59, 108, 246, .35); }
  .switch:disabled { opacity: .6; cursor: progress; transform: none; }
  .switch .spin { display: inline-block; } .switch.busy .spin { animation: spin .6s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .trail { display: flex; justify-content: center; align-items: center; gap: 8px; flex-wrap: wrap; margin-top: 22px; min-height: 28px; }
  .trail .hop { padding: 3px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; color: #fff; font-family: ui-monospace, Menlo, monospace; animation: pop .35s ease; }
  .trail .arrow { color: var(--muted); font-size: 12px; }
  .stats { color: var(--muted); font-size: 13px; margin-top: 14px; }
</style>
</head>
<body>
<main>
  <header>
    <a class="brand" href="/"><span class="logo">&#128666;</span><span><b>Nodo Ruta</b><small>__SERVICE__</small></span></a>
    <nav>__NAV__</nav>
  </header>
  __BODY__
  <div class="instance" id="instance">
    <h3>Instance serving you</h3>
    <div class="server" id="server"><span class="rack">&#128421;</span><span class="led"></span><code id="instance-id">__INSTANCE__</code></div>
    <button class="switch" id="switch" type="button"><span class="spin">&#128260;</span> Switch instance</button>
    <div class="trail" id="trail"></div>
    <div class="stats" id="stats">Press the button: the load balancer may send you to another instance.</div>
  </div>
</main>
<script>
  const el = id => document.getElementById(id);
  const getJson = path => fetch(path, { headers: { Accept: 'application/json' }, cache: 'no-store' });
  function cell(row, text) { row.insertCell().textContent = text; }
  function chip(text, kind) {
    const span = document.createElement('span');
    span.className = 'chip ' + kind;
    span.textContent = text;
    return span;
  }
__SCRIPT__
  (function () {
    const hueOf = id => { let h = 0; for (const c of id) h = (h * 31 + c.charCodeAt(0)) % 360; return h; };
    const colorOf = id => 'hsl(' + hueOf(id) + ' 70% 48%)';
    const box = el('instance'), server = el('server'), button = el('switch');
    const trail = [el('instance-id').textContent];
    const counts = { [trail[0]]: 1 };
    function paint(id) {
      box.style.setProperty('--hue', colorOf(id));
      el('instance-id').textContent = id;
      server.classList.remove('swap'); void server.offsetWidth; server.classList.add('swap');
    }
    function renderTrail() {
      const nodes = [];
      trail.slice(-6).forEach((id, i) => {
        if (i) { const a = document.createElement('span'); a.className = 'arrow'; a.textContent = '\u2192'; nodes.push(a); }
        const hop = document.createElement('span'); hop.className = 'hop'; hop.textContent = id; hop.style.background = colorOf(id); nodes.push(hop);
      });
      el('trail').replaceChildren(...nodes);
      const ids = Object.keys(counts);
      el('stats').textContent = ids.length + ' instance' + (ids.length === 1 ? '' : 's') + ' seen \u00b7 ' + trail.length + ' request' + (trail.length === 1 ? '' : 's');
    }
    paint(trail[0]); renderTrail();
    button.addEventListener('click', async () => {
      button.disabled = true; button.classList.add('busy');
      try {
        const response = await fetch('/health', { headers: { Accept: 'application/json' }, cache: 'no-store' });
        const id = response.headers.get('x-instance-id');
        if (id) { trail.push(id); counts[id] = (counts[id] || 0) + 1; paint(id); renderTrail(); }
      } catch (error) {
        el('stats').textContent = 'The service does not answer right now.';
      } finally {
        button.disabled = false; button.classList.remove('busy');
      }
    });
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
