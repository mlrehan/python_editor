import React, { useEffect, useRef, useState } from 'react';

/*
 * Renders one rich notebook output (HTML, Markdown, LaTeX, JavaScript, Plotly) inside a sandboxed
 * iframe served by /api/v1/output-frame. The sandbox has allow-scripts but NOT allow-same-origin, so
 * output code runs on an opaque origin: it can draw charts and run widgets' scripts, but it cannot
 * read the app's login token, cookies or DOM. Output HTML is never inserted into the app page itself.
 */

export type FrameMime =
  | 'text/html'
  | 'text/markdown'
  | 'text/latex'
  | 'application/javascript'
  | 'application/vnd.plotly.v1+json';

interface OutputFrameProps {
  mime: FrameMime;
  data: unknown;
}

const FRAME_URL = '/api/v1/output-frame';
const SANDBOX = 'allow-scripts allow-popups allow-popups-to-escape-sandbox allow-downloads';

// Colours of the current app theme, applied inside the frame
function readTheme() {
  const css = getComputedStyle(document.documentElement);
  const v = (name: string) => css.getPropertyValue(name).trim();
  const isLight = document.documentElement.getAttribute('data-theme') === 'light';
  return {
    fg: v('--text-main'),
    muted: v('--text-secondary'),
    border: v('--border-main'),
    accent: v('--accent'),
    codeBg: v('--bg-card'),
    rowAlt: isLight ? 'rgba(15,23,42,0.04)' : 'rgba(148,163,184,0.08)',
    scheme: isLight ? 'light' : 'dark',
  };
}

export const OutputFrame: React.FC<OutputFrameProps> = ({ mime, data }) => {
  const frameRef = useRef<HTMLIFrameElement>(null);
  const [height, setHeight] = useState(24);
  const [ready, setReady] = useState(false);
  const [themeKey, setThemeKey] = useState(0);

  // Messages from this frame only (identified by its window, since its origin is opaque)
  useEffect(() => {
    const onMessage = (e: MessageEvent) => {
      if (!frameRef.current || e.source !== frameRef.current.contentWindow) return;
      const msg = e.data as { source?: string; type?: string; height?: number };
      if (msg?.source !== 'pcs-output-frame') return;
      if (msg.type === 'ready') setReady(true);
      if (msg.type === 'height' && typeof msg.height === 'number') setHeight(Math.max(8, Math.min(msg.height, 20000)));
    };
    window.addEventListener('message', onMessage);
    return () => window.removeEventListener('message', onMessage);
  }, []);

  // Re-render with the new colours when the app theme changes
  useEffect(() => {
    const observer = new MutationObserver(() => setThemeKey((k) => k + 1));
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!ready || !frameRef.current?.contentWindow) return;
    // The frame's origin is opaque, so '*' is the only target that reaches it; the payload is the
    // output itself, which the frame is meant to display
    frameRef.current.contentWindow.postMessage({ type: 'render', mime, data, theme: readTheme() }, '*');
  }, [ready, mime, data, themeKey]);

  return (
    <iframe
      ref={frameRef}
      src={FRAME_URL}
      sandbox={SANDBOX}
      title={`Output (${mime})`}
      data-testid="output-frame"
      data-mime={mime}
      loading="lazy"
      style={{ display: 'block', width: '100%', height: `${height}px`, border: 'none', margin: '4px 0', background: 'transparent' }}
    />
  );
};
