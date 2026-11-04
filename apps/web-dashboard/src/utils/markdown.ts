import { Marked, Tokens } from 'marked';
import DOMPurify from 'dompurify';
import { tokenizePython } from './pythonSyntax';

/**
 * Markdown cells: GitHub-flavoured Markdown (headings, lists, task lists, tables, links, images,
 * blockquotes, code blocks, strikethrough), inline HTML that notebooks commonly use for formatting
 * (<mark> highlight, <span style="color: ..."> text colour, <u>, <sub>, <sup>) and LaTeX maths
 * ($inline$ and $$block$$, typeset by KaTeX). Like Jupyter and Colab.
 *
 * The HTML is sanitised: scripts, event handlers, iframes, forms and javascript: links are removed,
 * and inline styles are limited to text and highlight colours. Notebooks can come from anyone.
 */

const escapeHtml = (s: string) =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

/** Python code blocks use the same colours as code cells */
function highlightPython(code: string): string {
  let html = '';
  let last = 0;
  for (const t of tokenizePython(code)) {
    if (t.start > last) html += escapeHtml(code.slice(last, t.start));
    const text = escapeHtml(code.slice(t.start, t.end));
    html += t.kind === 'text' ? text : `<span class="tok-${t.kind}">${text}</span>`;
    last = t.end;
  }
  return html + escapeHtml(code.slice(last));
}

const PYTHON_LANGS = new Set(['python', 'py', 'python3', 'ipython', 'ipython3']);

const marked = new Marked({ gfm: true, breaks: false });

marked.use({
  extensions: [
    {
      // $$ ... $$ on their own lines: display maths
      name: 'mathBlock',
      level: 'block',
      start: (src: string) => {
        const i = src.indexOf('$$');
        return i < 0 ? undefined : i;
      },
      tokenizer(src: string) {
        const m = /^\$\$([\s\S]+?)\$\$[ \t]*(?:\n+|$)/.exec(src);
        if (m) return { type: 'mathBlock', raw: m[0], text: m[1].trim() };
        return undefined;
      },
      renderer: (token: Tokens.Generic) =>
        `<div class="md-math md-math-block" data-tex="${escapeHtml(token.text)}">${escapeHtml(`$$${token.text}$$`)}</div>\n`,
    },
    {
      // $ ... $ inside text: inline maths (not "$5 and $6": no space inside the dollars, no digit after)
      name: 'mathInline',
      level: 'inline',
      start: (src: string) => {
        const i = src.indexOf('$');
        return i < 0 ? undefined : i;
      },
      tokenizer(src: string) {
        const m = /^\$(?!\$)(?!\s)((?:\\\$|[^$\n])+?)(?<!\s)\$(?!\d)/.exec(src);
        if (m) return { type: 'mathInline', raw: m[0], text: m[1] };
        return undefined;
      },
      renderer: (token: Tokens.Generic) =>
        `<span class="md-math" data-tex="${escapeHtml(token.text)}">${escapeHtml(`$${token.text}$`)}</span>`,
    },
  ],
  renderer: {
    code({ text, lang }: Tokens.Code) {
      const language = (lang || '').trim().split(/\s+/)[0].toLowerCase();
      const body = PYTHON_LANGS.has(language) ? highlightPython(text) : escapeHtml(text);
      const label = language ? `<span class="md-code-lang">${escapeHtml(language)}</span>` : '';
      return `<pre class="md-code">${label}<code class="language-${escapeHtml(language || 'text')}">${body}</code></pre>\n`;
    },
  },
});

// Only colours survive in inline styles (text colour and highlight); everything else could cover
// or imitate the page
const SAFE_STYLE = /^\s*(color|background-color|background)\s*:\s*(#[0-9a-f]{3,8}|rgba?\([\d\s.,%]+\)|[a-z]+)\s*$/i;

let hooksInstalled = false;
function installHooks() {
  if (hooksInstalled) return;
  hooksInstalled = true;
  DOMPurify.addHook('uponSanitizeAttribute', (_node, data) => {
    if (data.attrName === 'style') {
      const kept = data.attrValue
        .split(';')
        .filter((decl) => SAFE_STYLE.test(decl))
        .join('; ');
      if (kept) data.attrValue = kept;
      else data.keepAttr = false;
    }
  });
  DOMPurify.addHook('afterSanitizeAttributes', (node) => {
    if (node.tagName === 'A' && node.getAttribute('href')) {
      node.setAttribute('target', '_blank');
      node.setAttribute('rel', 'noopener noreferrer nofollow');
    }
    if (node.tagName === 'INPUT') {
      // Task-list checkboxes are shown, not edited, in the rendered view
      node.setAttribute('disabled', '');
    }
  });
}

/** Markdown source -> safe HTML */
export function renderMarkdown(source: string): string {
  installHooks();
  const html = marked.parse(source ?? '', { async: false }) as string;
  return DOMPurify.sanitize(html, {
    ADD_ATTR: ['target', 'data-tex'],
    FORBID_TAGS: ['style', 'form', 'button', 'textarea', 'select', 'iframe', 'object', 'embed'],
    FORBID_ATTR: ['autofocus'],
  });
}

let katexLoad: Promise<typeof import('katex')['default']> | null = null;

/** Typesets the maths placeholders inside `root` (KaTeX loads on first use) */
export async function typesetMath(root: HTMLElement): Promise<void> {
  const nodes = Array.from(root.querySelectorAll<HTMLElement>('.md-math[data-tex]'));
  if (!nodes.length) return;
  if (!katexLoad) {
    katexLoad = Promise.all([import('katex'), import('katex/dist/katex.min.css')]).then(([m]) => m.default);
  }
  const katex = await katexLoad;
  for (const node of nodes) {
    if (!node.isConnected) continue;
    const tex = node.getAttribute('data-tex') ?? '';
    try {
      katex.render(tex, node, { displayMode: node.classList.contains('md-math-block'), throwOnError: false, output: 'htmlAndMathml' });
      node.removeAttribute('data-tex');
    } catch {
      node.textContent = tex;
    }
  }
}
