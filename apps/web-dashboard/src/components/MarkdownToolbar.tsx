import React, { useEffect, useRef, useState } from 'react';
import {
  Bold,
  Italic,
  Strikethrough,
  Code,
  Highlighter,
  Palette,
  List,
  ListOrdered,
  ListChecks,
  IndentIncrease,
  IndentDecrease,
  Link2,
  Image as ImageIcon,
  Quote,
  Minus,
  SquareCode,
  Sigma,
  ChevronDown,
  Columns2,
  Heading,
} from 'lucide-react';
import { TextEdit } from '../utils/lineComments';
import { applyTextareaEdit } from '../utils/textareaEdit';
import {
  applyColor,
  BlockFormat,
  continueList,
  InlineFormat,
  insertCodeBlock,
  insertDivider,
  insertImage,
  insertLink,
  insertMathBlock,
  isListLine,
  linkAt,
  ListKind,
  setBlock,
  shiftList,
  toggleInline,
  toggleList,
  toggleQuote,
} from '../utils/markdownFormat';

const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform);
const MOD = isMac ? '⌘' : 'Ctrl';

const CODE_LANGUAGES = ['python', 'bash', 'sql', 'json', 'javascript', 'html', 'css', 'yaml', 'text'];
const COLORS: Array<{ name: string; value: string | null }> = [
  { name: 'Default', value: null },
  { name: 'Red', value: '#dc2626' },
  { name: 'Orange', value: '#ea580c' },
  { name: 'Green', value: '#16a34a' },
  { name: 'Blue', value: '#2563eb' },
  { name: 'Purple', value: '#9333ea' },
  { name: 'Grey', value: '#6b7280' },
];
const MAX_EMBEDDED_IMAGE_BYTES = 1.5 * 1024 * 1024;

type Popover = null | 'heading' | 'color' | 'code' | 'math' | 'link' | 'image';

interface BtnProps {
  label: string;
  shortcut?: string;
  icon: React.ReactNode;
  onClick: () => void;
  testId: string;
  active?: boolean;
  /** Extra content after the icon (a caption, a dropdown arrow) */
  wide?: React.ReactNode;
}

function Btn({ label, shortcut, icon, onClick, testId, active, wide }: BtnProps) {
  return (
    <button
      type="button"
      className={`md-tb-btn${active ? ' is-active' : ''}${wide ? ' md-tb-btn--wide' : ''}`}
      onClick={onClick}
      title={shortcut ? `${label} (${shortcut})` : label}
      aria-label={label}
      aria-pressed={active}
      data-testid={testId}
    >
      {icon}
      {wide}
    </button>
  );
}

const Sep = () => <span className="md-tb-sep" aria-hidden="true" />;

interface MarkdownToolbarProps {
  /** The Markdown source editor this toolbar formats */
  editor: HTMLTextAreaElement | null;
  /** Called when the browser could not record an edit natively (keeps the cell in sync) */
  onFallbackChange: (value: string) => void;
  /** Side-by-side live preview while editing */
  showPreview: boolean;
  onTogglePreview: () => void;
}

/**
 * Formatting toolbar and shortcuts for a Markdown (text) cell, so people can format text without
 * knowing Markdown. Every action edits the cell's Markdown source through the browser's undo
 * history (Ctrl+Z / Ctrl+Shift+Z undo and redo it), keeps the selection, and never takes the focus
 * away from the text.
 */
export const MarkdownToolbar: React.FC<MarkdownToolbarProps> = ({ editor, onFallbackChange, showPreview, onTogglePreview }) => {
  const [popover, setPopover] = useState<Popover>(null);
  const [linkText, setLinkText] = useState('');
  const [linkUrl, setLinkUrl] = useState('');
  const [imageUrl, setImageUrl] = useState('');
  const [imageAlt, setImageAlt] = useState('');
  const [imageError, setImageError] = useState('');
  const savedSelection = useRef<{ start: number; end: number } | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const apply = (fn: (value: string, start: number, end: number) => TextEdit | null, selection = savedSelection.current) => {
    const el = editor;
    if (!el) return;
    const start = selection?.start ?? el.selectionStart;
    const end = selection?.end ?? el.selectionEnd;
    const edit = fn(el.value, start, end);
    if (!edit) return;
    const recorded = applyTextareaEdit(el, edit.value, edit.selectionStart, edit.selectionEnd);
    if (!recorded) onFallbackChange(edit.value);
    el.focus();
  };
  const run = (fn: (value: string, start: number, end: number) => TextEdit | null) => {
    savedSelection.current = null;
    setPopover(null);
    apply(fn, null);
  };

  const inline = (format: InlineFormat) => run((v, s, e) => toggleInline(v, s, e, format));
  const block = (format: BlockFormat) => run((v, s, e) => setBlock(v, s, e, format));
  const list = (kind: ListKind) => run((v, s, e) => toggleList(v, s, e, kind));

  // Popovers with fields (link, image) remember the selection they will replace
  const openPopover = (which: Popover) => {
    if (popover === which) {
      setPopover(null);
      return;
    }
    if (editor) savedSelection.current = { start: editor.selectionStart, end: editor.selectionEnd };
    if (which === 'link' && editor) {
      const existing = linkAt(editor.value, editor.selectionStart);
      if (existing && editor.selectionStart === editor.selectionEnd) {
        savedSelection.current = { start: existing.from, end: existing.to };
        setLinkText(existing.text);
        setLinkUrl(existing.url);
      } else {
        setLinkText(editor.value.substring(editor.selectionStart, editor.selectionEnd));
        setLinkUrl('');
      }
    }
    if (which === 'image') {
      setImageUrl('');
      setImageAlt('');
      setImageError('');
    }
    setPopover(which);
  };

  const closePopover = (refocus = true) => {
    setPopover(null);
    if (refocus && editor) {
      editor.focus();
      const sel = savedSelection.current;
      if (sel) editor.setSelectionRange(sel.start, sel.end);
    }
    savedSelection.current = null;
  };

  const submitLink = (e: React.FormEvent) => {
    e.preventDefault();
    if (!linkUrl.trim()) return;
    apply((v, s, en) => insertLink(v, s, en, linkText.trim(), linkUrl.trim()));
    savedSelection.current = null;
    setPopover(null);
  };

  const submitImage = (url: string, alt: string) => {
    if (!url.trim()) return;
    apply((v, s, en) => insertImage(v, s, en, alt.trim(), url.trim()));
    savedSelection.current = null;
    setPopover(null);
  };

  // An image from this computer is stored in the notebook itself (as Jupyter does with attachments)
  const pickImageFile = (file: File | undefined) => {
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      setImageError('Please choose an image file (PNG, JPEG, GIF, SVG or WebP).');
      return;
    }
    if (file.size > MAX_EMBEDDED_IMAGE_BYTES) {
      setImageError('This image is larger than 1.5 MB. Use a smaller image, or a link to an image on the web.');
      return;
    }
    const reader = new FileReader();
    reader.onload = () => submitImage(String(reader.result), imageAlt || file.name.replace(/\.[^.]+$/, ''));
    reader.onerror = () => setImageError('The image could not be read.');
    reader.readAsDataURL(file);
  };

  // Close popovers on outside clicks and Escape
  useEffect(() => {
    if (!popover) return;
    const onDown = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) closePopover(false);
    };
    document.addEventListener('mousedown', onDown);
    return () => document.removeEventListener('mousedown', onDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [popover]);

  // Keyboard shortcuts in the text, and list-aware Enter / Tab
  useEffect(() => {
    const el = editor;
    if (!el) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.isComposing) return;
      const mod = isMac ? e.metaKey : e.ctrlKey;
      const handled = () => {
        e.preventDefault();
        e.stopPropagation();
      };
      if (mod && !e.altKey) {
        const key = e.key.toLowerCase();
        if (!e.shiftKey && (key === 'b' || e.code === 'KeyB')) return handled(), inline('bold');
        if (!e.shiftKey && (key === 'i' || e.code === 'KeyI')) return handled(), inline('italic');
        if (!e.shiftKey && (key === 'e' || e.code === 'KeyE')) return handled(), inline('code');
        if (!e.shiftKey && (key === 'k' || e.code === 'KeyK')) return handled(), openPopover('link');
        if (e.shiftKey && e.code === 'KeyS') return handled(), inline('strike');
        if (e.shiftKey && e.code === 'KeyH') return handled(), inline('highlight');
        if (e.shiftKey && e.code === 'Digit7') return handled(), list('number');
        if (e.shiftKey && e.code === 'Digit8') return handled(), list('bullet');
        if (e.shiftKey && e.code === 'Digit9') return handled(), list('task');
      }
      if (mod && e.altKey && !e.shiftKey) {
        if (e.code === 'Digit1') return handled(), block('h1');
        if (e.code === 'Digit2') return handled(), block('h2');
        if (e.code === 'Digit3') return handled(), block('h3');
        if (e.code === 'Digit0') return handled(), block('p');
      }
      if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey && !e.metaKey && !e.altKey) {
        const edit = continueList(el.value, el.selectionStart, el.selectionEnd);
        if (edit) {
          handled();
          if (!applyTextareaEdit(el, edit.value, edit.selectionStart, edit.selectionEnd)) onFallbackChange(edit.value);
        }
        return;
      }
      if (e.key === 'Tab' && !e.ctrlKey && !e.metaKey && !e.altKey && isListLine(el.value, el.selectionStart)) {
        handled();
        const edit = shiftList(el.value, el.selectionStart, el.selectionEnd, e.shiftKey);
        if (!applyTextareaEdit(el, edit.value, edit.selectionStart, edit.selectionEnd)) onFallbackChange(edit.value);
      }
    };
    el.addEventListener('keydown', onKey);
    return () => el.removeEventListener('keydown', onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editor, popover]);


  return (
    <div ref={rootRef} className="md-toolbar" role="toolbar" aria-label="Text formatting" data-testid="markdown-toolbar">
      <div className="md-tb-group md-tb-anchor">
        <Btn label="Text style" icon={<Heading size={14} />} wide={<><span>Style</span><ChevronDown size={12} /></>} onClick={() => openPopover('heading')} testId="md-heading-menu" active={popover === 'heading'} />
        {popover === 'heading' && (
          <div className="md-tb-pop" role="menu" data-testid="md-heading-options">
            {([
              ['p', 'Normal text', `${MOD}+Alt+0`, 'md-opt-p'],
              ['h1', 'Heading 1', `${MOD}+Alt+1`, 'md-opt-h1'],
              ['h2', 'Heading 2', `${MOD}+Alt+2`, 'md-opt-h2'],
              ['h3', 'Heading 3', `${MOD}+Alt+3`, 'md-opt-h3'],
            ] as Array<[BlockFormat, string, string, string]>).map(([fmt, label, sc, id]) => (
              <button key={fmt} type="button" role="menuitem" className={`md-tb-opt md-tb-opt--${fmt}`} onClick={() => block(fmt)} data-testid={id}>
                <span>{label}</span>
                <kbd>{sc}</kbd>
              </button>
            ))}
          </div>
        )}
      </div>
      <Sep />
      <div className="md-tb-group">
        <Btn label="Bold" shortcut={`${MOD}+B`} icon={<Bold size={14} />} onClick={() => inline('bold')} testId="md-bold" />
        <Btn label="Italic" shortcut={`${MOD}+I`} icon={<Italic size={14} />} onClick={() => inline('italic')} testId="md-italic" />
        <Btn label="Strikethrough" shortcut={`${MOD}+Shift+S`} icon={<Strikethrough size={14} />} onClick={() => inline('strike')} testId="md-strike" />
        <Btn label="Inline code" shortcut={`${MOD}+E`} icon={<Code size={14} />} onClick={() => inline('code')} testId="md-code" />
        <Btn label="Highlight" shortcut={`${MOD}+Shift+H`} icon={<Highlighter size={14} />} onClick={() => inline('highlight')} testId="md-highlight" />
        <div className="md-tb-anchor">
          <Btn label="Text colour" icon={<Palette size={14} />} onClick={() => openPopover('color')} testId="md-color" active={popover === 'color'} />
          {popover === 'color' && (
            <div className="md-tb-pop md-tb-pop--colors" role="menu" data-testid="md-color-options">
              {COLORS.map((c) => (
                <button
                  key={c.name}
                  type="button"
                  role="menuitem"
                  className="md-tb-swatch"
                  title={c.name}
                  aria-label={c.name}
                  style={{ background: c.value ?? 'transparent' }}
                  onClick={() => {
                    apply((v, s, e) => applyColor(v, s, e, c.value));
                    savedSelection.current = null;
                    setPopover(null);
                  }}
                  data-testid={`md-color-${c.name.toLowerCase()}`}
                >
                  {c.value ? '' : 'A'}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
      <Sep />
      <div className="md-tb-group">
        <Btn label="Bulleted list" shortcut={`${MOD}+Shift+8`} icon={<List size={14} />} onClick={() => list('bullet')} testId="md-bullets" />
        <Btn label="Numbered list" shortcut={`${MOD}+Shift+7`} icon={<ListOrdered size={14} />} onClick={() => list('number')} testId="md-numbers" />
        <Btn label="Checklist" shortcut={`${MOD}+Shift+9`} icon={<ListChecks size={14} />} onClick={() => list('task')} testId="md-tasks" />
        <Btn label="Decrease indent" shortcut="Shift+Tab" icon={<IndentDecrease size={14} />} onClick={() => run((v, s, e) => shiftList(v, s, e, true))} testId="md-outdent" />
        <Btn label="Increase indent" shortcut="Tab" icon={<IndentIncrease size={14} />} onClick={() => run((v, s, e) => shiftList(v, s, e, false))} testId="md-indent" />
      </div>
      <Sep />
      <div className="md-tb-group">
        <div className="md-tb-anchor">
          <Btn label="Link" shortcut={`${MOD}+K`} icon={<Link2 size={14} />} onClick={() => openPopover('link')} testId="md-link" active={popover === 'link'} />
          {popover === 'link' && (
            <form className="md-tb-pop md-tb-form" onSubmit={submitLink} data-testid="md-link-form">
              <label>
                Text to show
                <input value={linkText} onChange={(e) => setLinkText(e.target.value)} placeholder="Link text" data-testid="md-link-text" />
              </label>
              <label>
                Web address
                <input
                  value={linkUrl}
                  onChange={(e) => setLinkUrl(e.target.value)}
                  placeholder="https://example.com"
                  autoFocus
                  data-testid="md-link-url"
                  onKeyDown={(e) => e.key === 'Escape' && (e.preventDefault(), closePopover())}
                />
              </label>
              <div className="md-tb-form-actions">
                <button type="button" onClick={() => closePopover()}>Cancel</button>
                <button type="submit" className="is-primary" disabled={!linkUrl.trim()} data-testid="md-link-apply">Apply</button>
              </div>
            </form>
          )}
        </div>
        <div className="md-tb-anchor">
          <Btn label="Image" icon={<ImageIcon size={14} />} onClick={() => openPopover('image')} testId="md-image" active={popover === 'image'} />
          {popover === 'image' && (
            <form
              className="md-tb-pop md-tb-form"
              onSubmit={(e) => {
                e.preventDefault();
                submitImage(imageUrl, imageAlt);
              }}
              data-testid="md-image-form"
            >
              <label>
                Image address
                <input value={imageUrl} onChange={(e) => setImageUrl(e.target.value)} placeholder="https://example.com/chart.png" autoFocus data-testid="md-image-url" />
              </label>
              <label>
                Description (for screen readers)
                <input value={imageAlt} onChange={(e) => setImageAlt(e.target.value)} placeholder="What the image shows" data-testid="md-image-alt" />
              </label>
              <div className="md-tb-form-actions">
                <button type="button" onClick={() => fileInputRef.current?.click()} data-testid="md-image-upload">From computer…</button>
                <input ref={fileInputRef} type="file" accept="image/*" hidden onChange={(e) => pickImageFile(e.target.files?.[0])} data-testid="md-image-file" />
                <button type="submit" className="is-primary" disabled={!imageUrl.trim()} data-testid="md-image-apply">Insert</button>
              </div>
              {imageError && <div className="md-tb-error" role="alert">{imageError}</div>}
            </form>
          )}
        </div>
        <Btn label="Quote" icon={<Quote size={14} />} onClick={() => run(toggleQuote)} testId="md-quote" />
        <Btn label="Divider" icon={<Minus size={14} />} onClick={() => run(insertDivider)} testId="md-divider" />
      </div>
      <Sep />
      <div className="md-tb-group">
        <div className="md-tb-anchor">
          <Btn label="Code block" icon={<SquareCode size={14} />} wide={<ChevronDown size={12} />} onClick={() => openPopover('code')} testId="md-codeblock" active={popover === 'code'} />
          {popover === 'code' && (
            <div className="md-tb-pop" role="menu" data-testid="md-code-languages">
              <div className="md-tb-pop-title">Code block language</div>
              {CODE_LANGUAGES.map((lang) => (
                <button key={lang} type="button" role="menuitem" className="md-tb-opt" onClick={() => run((v, s, e) => insertCodeBlock(v, s, e, lang === 'text' ? '' : lang))} data-testid={`md-code-${lang}`}>
                  {lang === 'text' ? 'Plain text' : lang[0].toUpperCase() + lang.slice(1)}
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="md-tb-anchor">
          <Btn label="Maths" icon={<Sigma size={14} />} wide={<ChevronDown size={12} />} onClick={() => openPopover('math')} testId="md-math" active={popover === 'math'} />
          {popover === 'math' && (
            <div className="md-tb-pop" role="menu" data-testid="md-math-options">
              <button type="button" role="menuitem" className="md-tb-opt" onClick={() => inline('math')} data-testid="md-math-inline">
                <span>Inline maths</span>
                <kbd>$x^2$</kbd>
              </button>
              <button type="button" role="menuitem" className="md-tb-opt" onClick={() => run(insertMathBlock)} data-testid="md-math-block">
                <span>Maths block</span>
                <kbd>$$ … $$</kbd>
              </button>
            </div>
          )}
        </div>
      </div>
      <span className="md-tb-spacer" />
      <Btn
        label={showPreview ? 'Hide live preview' : 'Show live preview'}
        icon={<Columns2 size={14} />}
        onClick={onTogglePreview}
        testId="md-live-preview"
        active={showPreview}
      />
    </div>
  );
};
