"""
Sandboxed renderer for rich notebook outputs (HTML, Markdown, LaTeX, JavaScript, Plotly).

The browser loads this page in an <iframe sandbox="allow-scripts ..."> WITHOUT allow-same-origin, so it
runs on an opaque origin: output code (a DataFrame Styler, a Plotly figure, any display(HTML(...)))
can run its scripts but cannot read the app's storage, cookies or DOM. That is how Jupyter and Colab
isolate outputs, and it is required here because guest notebooks are shared.

The parent posts {type: "render", mime, data, theme}; the frame answers {type: "height", height}.
Library scripts (KaTeX, marked, Plotly) load from public CDNs only when an output needs them.
"""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

OUTPUT_FRAME_PATH = "/api/v1/output-frame"

# Applied to this page only (the security middleware keeps it instead of the app-wide policy)
OUTPUT_FRAME_CSP = (
    "default-src 'none'; "
    "script-src 'unsafe-inline' 'unsafe-eval' https: blob: data:; "
    "style-src 'unsafe-inline' https:; "
    "img-src https: http: data: blob:; "
    "font-src https: data:; "
    "media-src https: data: blob:; "
    "connect-src https: data: blob:; "
    "frame-ancestors 'self'"
)

OUTPUT_FRAME_HTML = r"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root { --fg: #e2e8f0; --muted: #94a3b8; --border: #334155; --accent: #60a5fa; --code-bg: #0f172a; --row-alt: rgba(148,163,184,0.08); color-scheme: dark; }
  html, body { margin: 0; padding: 0; background: transparent; }
  body { color: var(--fg); font: 13px/1.55 Inter, system-ui, -apple-system, "Segoe UI", sans-serif; overflow-x: auto; overflow-y: hidden; }
  #root { padding: 2px 1px; }
  a { color: var(--accent); }
  img, svg, canvas, video { max-width: 100%; }
  pre, code { font-family: "JetBrains Mono", "Fira Code", Consolas, monospace; font-size: 12.5px; }
  pre { background: var(--code-bg); padding: 10px 12px; border-radius: 6px; overflow: auto; }
  table { border-collapse: collapse; font-size: 12.5px; }
  th, td { padding: 4px 10px; border-bottom: 1px solid var(--border); }
  th { font-weight: 600; }
  tbody tr:nth-child(odd) { background: var(--row-alt); }
  blockquote { margin: 6px 0; padding: 2px 12px; border-left: 3px solid var(--border); color: var(--muted); }
  .md h1, .md h2, .md h3 { line-height: 1.25; margin: 0.6em 0 0.35em; }
  .md p { margin: 0.45em 0; }
  .error { color: #f87171; font-family: monospace; white-space: pre-wrap; }
</style>
</head>
<body>
<div id="root"></div>
<script>
(function () {
  var root = document.getElementById('root');
  window.element = root; // Jupyter's application/javascript outputs write into `element`

  // This frame has no origin of its own (sandbox without allow-same-origin), so the browser throws on
  // localStorage, sessionStorage and document.cookie. Libraries such as Plotly and Bokeh touch them;
  // give outputs private in-memory versions instead (they never reach the app's real storage).
  function memoryStorage() {
    var data = {};
    return {
      getItem: function (k) { return Object.prototype.hasOwnProperty.call(data, k) ? data[k] : null; },
      setItem: function (k, v) { data[k] = String(v); },
      removeItem: function (k) { delete data[k]; },
      clear: function () { data = {}; },
      key: function (i) { return Object.keys(data)[i] || null; },
      get length() { return Object.keys(data).length; }
    };
  }
  ['localStorage', 'sessionStorage'].forEach(function (name) {
    try { Object.defineProperty(window, name, { value: memoryStorage(), configurable: true }); } catch (e) {}
  });
  try { Object.defineProperty(document, 'cookie', { get: function () { return ''; }, set: function () {}, configurable: true }); } catch (e) {}
  var KATEX = 'https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/';
  var MARKED = 'https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js';
  var PLOTLY = 'https://cdn.plot.ly/plotly-2.35.2.min.js';

  function post(msg) { msg.source = 'pcs-output-frame'; parent.postMessage(msg, '*'); }
  function reportHeight() {
    post({ type: 'height', height: Math.ceil(document.documentElement.getBoundingClientRect().height) });
  }
  new ResizeObserver(reportHeight).observe(document.documentElement);

  var loaded = {};
  function loadScript(src) {
    if (!loaded[src]) {
      loaded[src] = new Promise(function (resolve, reject) {
        var s = document.createElement('script');
        s.src = src; s.onload = resolve; s.onerror = function () { reject(new Error('Could not load ' + src)); };
        document.head.appendChild(s);
      });
    }
    return loaded[src];
  }
  function loadCss(href) {
    var l = document.createElement('link'); l.rel = 'stylesheet'; l.href = href; document.head.appendChild(l);
  }
  function katexReady() {
    if (!loaded.katexCss) { loaded.katexCss = true; loadCss(KATEX + 'katex.min.css'); }
    return loadScript(KATEX + 'katex.min.js').then(function () { return loadScript(KATEX + 'contrib/auto-render.min.js'); });
  }
  function renderMath(el) {
    window.renderMathInElement(el, {
      delimiters: [
        { left: '$$', right: '$$', display: true },
        { left: '\\[', right: '\\]', display: true },
        { left: '\\begin{equation}', right: '\\end{equation}', display: true },
        { left: '\\begin{align}', right: '\\end{align}', display: true },
        { left: '\\begin{align*}', right: '\\end{align*}', display: true },
        { left: '$', right: '$', display: false },
        { left: '\\(', right: '\\)', display: false }
      ],
      throwOnError: false
    });
  }
  // innerHTML does not run <script>: re-create them in order (external ones finish loading first)
  function runScripts(container) {
    var scripts = Array.prototype.slice.call(container.querySelectorAll('script'));
    return scripts.reduce(function (chain, old) {
      return chain.then(function () {
        return new Promise(function (resolve) {
          var s = document.createElement('script');
          for (var i = 0; i < old.attributes.length; i++) s.setAttribute(old.attributes[i].name, old.attributes[i].value);
          if (old.src) { s.onload = resolve; s.onerror = resolve; } else { s.text = old.textContent; }
          old.parentNode.replaceChild(s, old);
          if (!old.src) resolve();
        });
      });
    }, Promise.resolve());
  }
  function applyTheme(theme) {
    if (!theme) return;
    var st = document.documentElement.style;
    var vars = { fg: 'fg', muted: 'muted', border: 'border', accent: 'accent', codeBg: 'code-bg', rowAlt: 'row-alt' };
    Object.keys(vars).forEach(function (key) {
      if (theme[key]) st.setProperty('--' + vars[key], theme[key]);
    });
    st.colorScheme = theme.scheme || 'dark';
  }
  function showError(err) {
    var div = document.createElement('div'); div.className = 'error'; div.textContent = String(err && err.message || err);
    root.appendChild(div);
  }

  function render(msg) {
    applyTheme(msg.theme);
    var mime = msg.mime, data = msg.data;
    root.className = ''; root.innerHTML = '';
    var work;
    if (mime === 'text/html') {
      root.innerHTML = data;
      work = runScripts(root).then(function () {
        if (/\$|\\\(|\\\[/.test(root.textContent || '') && /katex|\$\$/.test(data)) return katexReady().then(function () { renderMath(root); });
      });
    } else if (mime === 'text/markdown') {
      root.className = 'md';
      work = loadScript(MARKED).then(function () {
        root.innerHTML = window.marked.parse(data);
        return katexReady().then(function () { renderMath(root); }, function () {});
      }, function () { root.textContent = data; });
    } else if (mime === 'text/latex') {
      root.textContent = data;
      work = katexReady().then(function () { renderMath(root); });
    } else if (mime === 'application/javascript') {
      var s = document.createElement('script'); s.text = data; root.appendChild(s);
      work = Promise.resolve();
    } else if (mime === 'application/vnd.plotly.v1+json') {
      work = loadScript(PLOTLY).then(function () {
        var div = document.createElement('div'); root.appendChild(div);
        var layout = Object.assign({ autosize: true }, data.layout || {});
        return window.Plotly.newPlot(div, data.data || [], layout, Object.assign({ responsive: true, displaylogo: false }, data.config || {}));
      });
    } else {
      root.textContent = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
      work = Promise.resolve();
    }
    work.catch(showError).then(function () {
      reportHeight(); setTimeout(reportHeight, 250); setTimeout(reportHeight, 1200);
      post({ type: 'rendered' });
    });
  }

  window.addEventListener('message', function (e) {
    if (e.source !== parent || !e.data || e.data.type !== 'render') return;
    render(e.data);
  });
  post({ type: 'ready' });
})();
</script>
</body>
</html>
"""


@router.get("/output-frame", include_in_schema=False)
async def output_frame() -> HTMLResponse:
    return HTMLResponse(
        OUTPUT_FRAME_HTML,
        headers={
            "Content-Security-Policy": OUTPUT_FRAME_CSP,
            "Cache-Control": "public, max-age=300",
        },
    )
