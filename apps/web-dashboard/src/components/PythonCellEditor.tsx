import React, { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import { api } from '../services/api';
import {
  Box,
  Layers,
  Variable,
  Key,
  AlertTriangle,
} from 'lucide-react';

interface CompletionItem {
  label: string;
  type: string;
  detail?: string;
  documentation?: string;
  insert_text?: string;
}

interface DiagnosticItem {
  from_line: number;
  from_col: number;
  to_line: number;
  to_col: number;
  message: string;
  severity: string;
}

interface SignatureItem {
  name: string;
  signature: string;
  params: string[];
  docstring?: string;
  index: number;
}

interface PythonCellEditorProps {
  cellId: string;
  code: string;
  onChange: (newCode: string) => void;
  onRunCurrentCell: (cellId: string, code: string) => void;
  onRunAndAdvance: (cellId: string, code: string) => void;
  onRunAndInsertBelow: (cellId: string, code: string) => void;
  onFocus?: () => void;
  notebookContext?: string[];
  sessionId?: string;
  placeholder?: string;
  readOnly?: boolean;
  editorRef?: (el: HTMLTextAreaElement | null) => void;
  customHeight?: number;
  onHeightChange?: (cellId: string, height: number | undefined) => void;
}

// Compute caret (x, y) coordinates relative to the textarea
function getCaretCoordinates(textarea: HTMLTextAreaElement, position: number) {
  const div = document.createElement('div');
  const style = window.getComputedStyle(textarea);

  const propertiesToCopy = [
    'direction', 'boxSizing', 'width', 'height', 'overflowX', 'overflowY',
    'borderTopWidth', 'borderRightWidth', 'borderBottomWidth', 'borderLeftWidth',
    'borderStyle', 'paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft',
    'fontStyle', 'fontVariant', 'fontWeight', 'fontStretch', 'fontSize',
    'fontSizeAdjust', 'lineHeight', 'fontFamily', 'textAlign', 'textTransform',
    'textIndent', 'textDecoration', 'letterSpacing', 'wordSpacing', 'tabSize',
    'whiteSpace', 'wordBreak',
  ];

  propertiesToCopy.forEach((prop: any) => {
    (div.style as any)[prop] = (style as any)[prop];
  });

  div.style.position = 'absolute';
  div.style.top = '-9999px';
  div.style.left = '-9999px';
  div.style.visibility = 'hidden';
  div.style.whiteSpace = 'pre-wrap';

  const textBefore = textarea.value.substring(0, position);
  div.textContent = textBefore;

  const span = document.createElement('span');
  span.textContent = textarea.value.substring(position) || '.';
  div.appendChild(span);

  document.body.appendChild(div);

  const coordinates = {
    top: span.offsetTop + parseInt(style.borderTopWidth || '0', 10),
    left: span.offsetLeft + parseInt(style.borderLeftWidth || '0', 10),
    lineHeight: parseInt(style.lineHeight || '21', 10),
  };

  document.body.removeChild(div);
  return coordinates;
}

export const PythonCellEditor: React.FC<PythonCellEditorProps> = ({
  cellId,
  code,
  onChange,
  onRunCurrentCell,
  onRunAndAdvance,
  onRunAndInsertBelow,
  onFocus,
  notebookContext = [],
  sessionId,
  placeholder = '# Write Python code here...',
  readOnly = false,
  editorRef,
  customHeight,
  onHeightChange,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const signatureRef = useRef<HTMLDivElement>(null);
  const gutterRef = useRef<HTMLDivElement>(null);
  const diagnosticLayerRef = useRef<HTMLDivElement>(null);
  const autocompleteReqIdRef = useRef(0);

  // Vertical Resizing State
  const [liveHeight, setLiveHeight] = useState<number | undefined>(customHeight);
  const [isResizing, setIsResizing] = useState(false);

  useEffect(() => {
    setLiveHeight(customHeight);
  }, [customHeight]);

  const handleScroll = (e: React.UIEvent<HTMLTextAreaElement>) => {
    if (gutterRef.current) {
      gutterRef.current.scrollTop = e.currentTarget.scrollTop;
    }
    if (diagnosticLayerRef.current) {
      diagnosticLayerRef.current.scrollTop = e.currentTarget.scrollTop;
    }
    if ((isDropdownOpen || activeSignature) && textareaRef.current) {
      updatePopupPositions(textareaRef.current.selectionStart);
    }
  };

  const handleResizeMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsResizing(true);
    const startY = e.clientY;
    const initialH = liveHeight || textareaRef.current?.clientHeight || 90;

    const handleMouseMove = (moveEvent: MouseEvent) => {
      const delta = moveEvent.clientY - startY;
      const clamped = Math.max(80, Math.min(800, initialH + delta));
      setLiveHeight(clamped);
      document.body.style.cursor = 'ns-resize';
      document.body.style.userSelect = 'none';
    };

    const handleMouseUp = (upEvent: MouseEvent) => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      setIsResizing(false);
      const delta = upEvent.clientY - startY;
      const finalH = Math.max(80, Math.min(800, initialH + delta));
      if (onHeightChange) {
        onHeightChange(cellId, finalH);
      }
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
  };

  const handleResetHeight = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setLiveHeight(undefined);
    if (onHeightChange) {
      onHeightChange(cellId, undefined);
    }
  };

  // Autocomplete state
  const [completions, setCompletions] = useState<CompletionItem[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [dropdownPos, setDropdownPos] = useState<{ top: number; left: number; placement: 'above' | 'below' }>({
    top: 0,
    left: 0,
    placement: 'below',
  });

  // Signature help state
  const [activeSignature, setActiveSignature] = useState<SignatureItem | null>(null);
  const [signaturePos, setSignaturePos] = useState<{ top: number; left: number; placement: 'above' | 'below' }>({
    top: 0,
    left: 0,
    placement: 'above',
  });

  // Diagnostics (real Python syntax errors and missing imports)
  const [diagnostics, setDiagnostics] = useState<DiagnosticItem[]>([]);

  const lines = useMemo(() => code.split('\n'), [code]);
  const contextKey = useMemo(() => (notebookContext || []).join('\n---\n'), [notebookContext]);

  // 1. Fetch Diagnostics (Debounced 300ms)
  const fetchDiagnostics = useCallback(async () => {
    if (!code.trim()) {
      setDiagnostics([]);
      return;
    }
    try {
      const res = await api.getDiagnostics(code, notebookContext, sessionId);
      setDiagnostics(res.diagnostics || []);
    } catch {
      // Quietly handle network or dev errors
    }
  }, [code, notebookContext, sessionId]);

  useEffect(() => {
    let isCancelled = false;
    const timer = setTimeout(async () => {
      if (!code.trim()) {
        setDiagnostics([]);
        return;
      }
      try {
        const res = await api.getDiagnostics(code, notebookContext, sessionId);
        if (!isCancelled) {
          setDiagnostics(res.diagnostics || []);
        }
      } catch {
        // Quietly handle network or dev errors
      }
    }, 300);

    return () => {
      isCancelled = true;
      clearTimeout(timer);
    };
  }, [code, contextKey, sessionId]);

  // Immediately re-fetch diagnostics upon kernel events (package install, kernel restart)
  useEffect(() => {
    const handleGlobalRefresh = () => {
      fetchDiagnostics();
    };
    window.addEventListener('pcs-refresh-diagnostics', handleGlobalRefresh);
    return () => {
      window.removeEventListener('pcs-refresh-diagnostics', handleGlobalRefresh);
    };
  }, [fetchDiagnostics]);

  // Helper to render signature with active parameter highlighted
  const renderSignatureHelp = useCallback((sig: SignatureItem) => {
    if (!sig.signature) return null;
    if (!sig.params || sig.params.length === 0 || sig.index === undefined || sig.index < 0 || sig.index >= sig.params.length) {
      return <div style={{ color: 'var(--border-accent)', fontWeight: 600 }}>{sig.signature}</div>;
    }

    const activeParam = sig.params[sig.index];
    if (!activeParam) {
      return <div style={{ color: 'var(--border-accent)', fontWeight: 600 }}>{sig.signature}</div>;
    }

    const regex = new RegExp(`(\\b\\*?${activeParam}\\b(?:=[^,)]*)?)`, 'g');
    const parts = sig.signature.split(regex);

    if (parts.length <= 1) {
      return <div style={{ color: 'var(--border-accent)', fontWeight: 600 }}>{sig.signature}</div>;
    }

    return (
      <div style={{ color: 'var(--border-accent)', fontWeight: 600 }}>
        {parts.map((part, i) => {
          const isParamMatch = part.replace(/^\*/, '').startsWith(activeParam);
          if (isParamMatch) {
            return (
              <span
                key={i}
                style={{
                  textDecoration: 'underline',
                  textDecorationThickness: '2px',
                  color: '#38bdf8',
                  fontWeight: 700,
                  backgroundColor: 'rgba(56, 189, 248, 0.15)',
                  padding: '1px 3px',
                  borderRadius: '3px',
                }}
              >
                {part}
              </span>
            );
          }
          return <span key={i}>{part}</span>;
        })}
      </div>
    );
  }, []);

  // Priority popup dismissal: closes autocomplete first, signature second
  const dismissTopmostPopup = useCallback((): boolean => {
    autocompleteReqIdRef.current++;
    if (isDropdownOpen) {
      setIsDropdownOpen(false);
      return true;
    }
    if (activeSignature) {
      setActiveSignature(null);
      return true;
    }
    return false;
  }, [isDropdownOpen, activeSignature]);

  // Dynamically compute caret coordinates and non-overlapping popup positioning
  const updatePopupPositions = useCallback((cursorIndex: number) => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    try {
      const coords = getCaretCoordinates(textarea, cursorIndex);
      const textareaRect = textarea.getBoundingClientRect();
      const scrollTop = textarea.scrollTop || 0;
      const scrollLeft = textarea.scrollLeft || 0;

      // Line number gutter width is 44px
      const cursorXInContainer = coords.left + 44 - scrollLeft;
      const cursorYInContainer = coords.top - scrollTop;
      const lineHeight = coords.lineHeight || 21;
      const lineTop = cursorYInContainer;
      const lineBottom = cursorYInContainer + lineHeight;

      // Viewport checks for vertical placement (above vs below cursor)
      const cursorViewportY = textareaRect.top + coords.top - scrollTop;
      const viewportHeight = window.innerHeight;
      const dropdownHeight = 260; // Max height of autocomplete dropdown
      const spaceBelow = viewportHeight - (cursorViewportY + lineHeight + 10);
      const spaceAbove = cursorViewportY - 10;

      // 1. Dropdown positioning (Google Colab style: below cursor if space permits, above if tight below)
      let dropTop: number;
      let dropPlacement: 'above' | 'below';

      if (spaceBelow < dropdownHeight && spaceAbove > spaceBelow) {
        // Open dropdown ABOVE cursor line
        dropTop = lineTop - 6;
        dropPlacement = 'above';
      } else {
        // Open dropdown BELOW cursor line
        dropTop = lineBottom + 6;
        dropPlacement = 'below';
      }

      // 2. Signature Help positioning (Google Colab style: opposite side of dropdown so they never collide)
      let sigTop: number;
      let sigPlacement: 'above' | 'below';

      if (dropPlacement === 'below') {
        // Dropdown is below -> place signature help ABOVE the cursor line
        // If space above in viewport is very tight (< 60px) and dropdown is NOT open, place signature help below
        if (!isDropdownOpen && spaceAbove < 60 && spaceBelow > spaceAbove) {
          sigTop = lineBottom + 6;
          sigPlacement = 'below';
        } else {
          sigTop = lineTop - 6;
          sigPlacement = 'above';
        }
      } else {
        // Dropdown is above -> place signature help BELOW the cursor line
        sigTop = lineBottom + 6;
        sigPlacement = 'below';
      }

      const containerWidth = containerRef.current?.clientWidth || 600;
      const dropdownWidth = 320;
      const sigWidth = 480;

      // Clamp horizontal positions within container bounds
      const dropLeft = Math.max(10, Math.min(cursorXInContainer + 8, containerWidth - dropdownWidth - 16));
      const sigLeft = Math.max(10, Math.min(cursorXInContainer + 8, containerWidth - sigWidth - 16));

      setDropdownPos({ top: dropTop, left: dropLeft, placement: dropPlacement });
      setSignaturePos({ top: sigTop, left: sigLeft, placement: sigPlacement });
    } catch {
      // Fallback
    }
  }, [isDropdownOpen]);

  // Synchronize active selection with visible scroll area
  useEffect(() => {
    if (!isDropdownOpen || !listRef.current) return;
    const container = listRef.current;
    const activeItem = container.children[selectedIndex] as HTMLElement | undefined;
    if (activeItem) {
      const itemTop = activeItem.offsetTop;
      const itemBottom = itemTop + activeItem.offsetHeight;
      const containerTop = container.scrollTop;
      const containerBottom = containerTop + container.clientHeight;

      if (itemTop < containerTop) {
        container.scrollTop = itemTop;
      } else if (itemBottom > containerBottom) {
        container.scrollTop = itemBottom - container.clientHeight;
      }
    }
  }, [selectedIndex, isDropdownOpen]);

  // Click outside to dismiss autocomplete dropdown & signature tooltip
  useEffect(() => {
    if (!isDropdownOpen && !activeSignature) return;

    const handlePointerDownOutside = (e: PointerEvent | MouseEvent) => {
      const target = e.target as Node | null;
      if (!target) return;

      // Inside dropdown or signature tooltip -> keep open
      if (dropdownRef.current && dropdownRef.current.contains(target)) return;
      if (signatureRef.current && signatureRef.current.contains(target)) return;

      // Inside this cell's textarea -> let textarea handle cursor placement
      if (textareaRef.current && textareaRef.current.contains(target)) return;

      // Clicked outside this editor
      autocompleteReqIdRef.current++;
      setIsDropdownOpen(false);
      setActiveSignature(null);
    };

    document.addEventListener('pointerdown', handlePointerDownOutside, true);
    return () => {
      document.removeEventListener('pointerdown', handlePointerDownOutside, true);
    };
  }, [isDropdownOpen, activeSignature]);

  // Global Escape handler to ensure dropdown and signature tooltip close with proper priority
  useEffect(() => {
    if (!isDropdownOpen && !activeSignature) return;

    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if ((e as any).__pcsHandledEscape) return;
        (e as any).__pcsHandledEscape = true;
        if (dismissTopmostPopup()) {
          e.preventDefault();
          e.stopPropagation();
          e.stopImmediatePropagation();
        }
      }
    };

    window.addEventListener('keydown', handleGlobalKeyDown, true);
    return () => {
      window.removeEventListener('keydown', handleGlobalKeyDown, true);
    };
  }, [isDropdownOpen, activeSignature, dismissTopmostPopup]);

  // Reposition on window resize
  useEffect(() => {
    const handleWindowResize = () => {
      if ((isDropdownOpen || activeSignature) && textareaRef.current) {
        updatePopupPositions(textareaRef.current.selectionStart);
      }
    };
    window.addEventListener('resize', handleWindowResize);
    return () => window.removeEventListener('resize', handleWindowResize);
  }, [isDropdownOpen, activeSignature, updatePopupPositions]);

  // 2. Trigger Autocomplete when cursor moves or code changes
  const triggerAutocomplete = useCallback(
    async (cursorIndex: number, explicit = false) => {
      if (readOnly || !textareaRef.current) return;

      const currentCode = textareaRef.current?.value ?? code;
      const textBeforeCursor = currentCode.substring(0, cursorIndex);
      const linesBefore = textBeforeCursor.split('\n');
      const currentLine = linesBefore.length;
      const currentCol = linesBefore[linesBefore.length - 1].length;
      const currentLineText = linesBefore[linesBefore.length - 1];

      // Extract current word/prefix and trigger symbol
      const match = currentLineText.match(/([a-zA-Z0-9_\.]+)$/);
      const token = match ? match[1] : '';

      // Check if cursor is inside unclosed function call parentheses
      let openParenCount = 0;
      for (let i = 0; i < textBeforeCursor.length; i++) {
        const ch = textBeforeCursor[i];
        if (ch === '(') openParenCount++;
        else if (ch === ')') openParenCount = Math.max(0, openParenCount - 1);
      }
      const isInsideParens = openParenCount > 0;

      const isDotTrigger = currentLineText.endsWith('.');
      const isWordTrigger = token.length >= 1 && (token.includes('.') || explicit || token.length >= 2 || (isInsideParens && token.length >= 1));

      if (!explicit && !isDotTrigger && !isWordTrigger && !isInsideParens) {
        autocompleteReqIdRef.current++;
        setIsDropdownOpen(false);
        setActiveSignature(null);
        return;
      }

      // Calculate prefix being completed (e.g. in "np.ar", prefix is "ar")
      let prefix = '';
      if (token.includes('.')) {
        const parts = token.split('.');
        prefix = parts[parts.length - 1];
      } else {
        prefix = token;
      }

      // Compute Caret Coordinates for floating dropdown & signature
      const reqId = ++autocompleteReqIdRef.current;
      updatePopupPositions(cursorIndex);

      try {
        const res = await api.getCompletions(currentCode, currentLine, currentCol, notebookContext, sessionId);
        if (reqId !== autocompleteReqIdRef.current) return;
        let items = res.completions || [];

        // Client-side filtering & intelligent ranking
        if (prefix) {
          const lowerPfx = prefix.toLowerCase();
          items = items.filter((item) => item.label.toLowerCase().includes(lowerPfx));
          items.sort((a, b) => {
            const aStarts = a.label.toLowerCase().startsWith(lowerPfx);
            const bStarts = b.label.toLowerCase().startsWith(lowerPfx);
            if (aStarts && !bStarts) return -1;
            if (!aStarts && bStarts) return 1;
            return a.label.localeCompare(b.label);
          });
        }

        // Dropdown should ONLY open if explicit (Ctrl+Space), dot trigger, or a non-empty word token
        // NOT on empty paren trigger like print(
        const shouldShowDropdown = items.length > 0 && (explicit || isDotTrigger || (token.length >= 1 && !currentLineText.endsWith('(')));

        if (shouldShowDropdown) {
          setCompletions(items);
          setSelectedIndex(0);
          if (listRef.current) {
            listRef.current.scrollTop = 0;
          }
          setIsDropdownOpen(true);
        } else {
          setIsDropdownOpen(false);
        }

        // Signature help (only when inside parentheses)
        if (isInsideParens && res.signatures && res.signatures.length > 0) {
          setActiveSignature(res.signatures[0]);
        } else {
          setActiveSignature(null);
        }
      } catch (err) {
        setIsDropdownOpen(false);
        setActiveSignature(null);
      }
    },
    [code, notebookContext, sessionId, readOnly, updatePopupPositions]
  );

  // Insert selected completion into textarea
  const acceptCompletion = useCallback(
    (item: CompletionItem) => {
      const el = textareaRef.current;
      if (!el) return;

      const currentValue = el.value;
      const cursorPos = el.selectionStart;

      // Extract the line up to the cursor
      const textBefore = currentValue.substring(0, cursorPos);
      const lines = textBefore.split('\n');
      const currentLine = lines[lines.length - 1];

      // Match the incomplete token being completed:
      // Case A: Member completion after a dot: e.g. "pd.re", "pd.read_c", "pd."
      // The prefix to replace is whatever follows the last dot on this line.
      const dotMatch = currentLine.match(/\.([a-zA-Z0-9_]*)$/);

      let replaceStart = cursorPos;
      if (dotMatch !== null) {
        const prefix = dotMatch[1];
        replaceStart = cursorPos - prefix.length;
      } else {
        // Case B: Standalone identifier: e.g. "pri", "im"
        const idMatch = currentLine.match(/([a-zA-Z0-9_]+)$/);
        if (idMatch !== null) {
          const prefix = idMatch[1];
          replaceStart = cursorPos - prefix.length;
        }
      }

      // Check for any matching identifier suffix immediately following cursor
      const textAfter = currentValue.substring(cursorPos);
      const firstLineAfter = textAfter.split('\n')[0];
      const suffixMatch = firstLineAfter.match(/^([a-zA-Z0-9_]+)/);
      const replaceEnd = suffixMatch ? cursorPos + suffixMatch[1].length : el.selectionEnd;

      const before = currentValue.substring(0, replaceStart);
      const after = currentValue.substring(replaceEnd);
      const insert = item.insert_text || item.label;
      const newCode = before + insert + after;
      const newCursorPos = before.length + insert.length;

      autocompleteReqIdRef.current++;
      onChange(newCode);
      setIsDropdownOpen(false);
      setActiveSignature(null);

      // Restore focus and update cursor position
      requestAnimationFrame(() => {
        if (textareaRef.current) {
          textareaRef.current.focus();
          textareaRef.current.setSelectionRange(newCursorPos, newCursorPos);
        }
      });
    },
    [onChange]
  );

  // 3. Keyboard Navigation in Code & Autocomplete
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // 1. Cross-platform Execution Shortcuts
    const isCtrlOrCmdEnter = (e.ctrlKey || e.metaKey) && e.key === 'Enter' && !e.shiftKey && !e.altKey;
    const isShiftEnter = e.shiftKey && e.key === 'Enter' && !e.ctrlKey && !e.metaKey && !e.altKey;
    const isAltEnter = e.altKey && e.key === 'Enter' && !e.ctrlKey && !e.metaKey;

    if (isCtrlOrCmdEnter) {
      e.preventDefault();
      autocompleteReqIdRef.current++;
      setIsDropdownOpen(false);
      setActiveSignature(null);
      onRunCurrentCell(cellId, e.currentTarget.value);
      return;
    }

    if (isShiftEnter) {
      e.preventDefault();
      autocompleteReqIdRef.current++;
      setIsDropdownOpen(false);
      setActiveSignature(null);
      onRunAndAdvance(cellId, e.currentTarget.value);
      return;
    }

    if (isAltEnter) {
      e.preventDefault();
      autocompleteReqIdRef.current++;
      setIsDropdownOpen(false);
      setActiveSignature(null);
      onRunAndInsertBelow(cellId, e.currentTarget.value);
      return;
    }

    // 2. Dropdown active keyboard handling
    if (isDropdownOpen && completions.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        e.stopPropagation();
        setSelectedIndex((prev) => (prev + 1) % completions.length);
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        e.stopPropagation();
        setSelectedIndex((prev) => (prev - 1 + completions.length) % completions.length);
        return;
      }
      if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault();
        e.stopPropagation();
        acceptCompletion(completions[selectedIndex]);
        return;
      }
    }

    // Dismiss popups on Escape with single-key priority
    if (e.key === 'Escape') {
      if ((e.nativeEvent as any)?.__pcsHandledEscape) {
        return;
      }
      (e.nativeEvent as any).__pcsHandledEscape = true;
      if (dismissTopmostPopup()) {
        e.preventDefault();
        e.stopPropagation();
        return;
      }
    }

    // 3. Manual Autocomplete Trigger (Ctrl+Space / Cmd+Space)
    if ((e.ctrlKey || e.metaKey) && e.key === ' ') {
      e.preventDefault();
      triggerAutocomplete(e.currentTarget.selectionStart, true);
      return;
    }

    // 4. Tab key: Indent 4 spaces if dropdown is closed
    if (e.key === 'Tab' && !isDropdownOpen) {
      e.preventDefault();
      const el = e.currentTarget;
      const start = el.selectionStart;
      const end = el.selectionEnd;
      const newCode = code.substring(0, start) + '    ' + code.substring(end);
      onChange(newCode);
      setTimeout(() => {
        el.selectionStart = el.selectionEnd = start + 4;
      }, 0);
      return;
    }

    // 5. Auto-closing pairs: (, [, {, ', "
    const pairs: Record<string, string> = { '(': ')', '[': ']', '{': '}', '"': '"', "'": "'" };
    if (pairs[e.key] && !e.ctrlKey && !e.metaKey) {
      const el = e.currentTarget;
      const start = el.selectionStart;
      const end = el.selectionEnd;
      if (start === end) {
        const closeChar = pairs[e.key];
        e.preventDefault();
        const newCode = code.substring(0, start) + e.key + closeChar + code.substring(end);
        onChange(newCode);
        setTimeout(() => {
          el.selectionStart = el.selectionEnd = start + 1;
          triggerAutocomplete(start + 1, false);
        }, 10);
        return;
      }
    }

    // 6. Auto-indentation after colon
    if (e.key === 'Enter') {
      const el = e.currentTarget;
      const cursor = el.selectionStart;
      const lineBeforeCursor = code.substring(0, cursor).split('\n').pop() || '';
      const matchIndent = lineBeforeCursor.match(/^(\s*)/);
      const currentIndent = matchIndent ? matchIndent[1] : '';
      const extraIndent = lineBeforeCursor.trim().endsWith(':') ? '    ' : '';

      if (currentIndent || extraIndent) {
        e.preventDefault();
        const insertText = '\n' + currentIndent + extraIndent;
        const newCode = code.substring(0, cursor) + insertText + code.substring(cursor);
        onChange(newCode);
        setTimeout(() => {
          el.selectionStart = el.selectionEnd = cursor + insertText.length;
        }, 0);
        return;
      }
    }
  };

  const handleInput = (e: React.FormEvent<HTMLTextAreaElement>) => {
    const val = e.currentTarget.value;
    onChange(val);
    const cursor = e.currentTarget.selectionStart;
    // Trigger autocomplete on typing
    setTimeout(() => {
      triggerAutocomplete(cursor, false);
    }, 10);
  };

  const handleClick = (e: React.MouseEvent<HTMLTextAreaElement>) => {
    if (isDropdownOpen) setIsDropdownOpen(false);
    triggerAutocomplete(e.currentTarget.selectionStart, false);
  };

  // Icon mapping for completion item types
  const renderItemIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'function':
      case 'method':
        return <span style={{ color: '#60a5fa', fontWeight: 700, fontSize: '11px', width: '16px', textAlign: 'center' }}>ƒ</span>;
      case 'module':
      case 'package':
        return <Box size={13} color="#f59e0b" />;
      case 'class':
        return <Layers size={13} color="#a855f7" />;
      case 'keyword':
        return <Key size={13} color="#ec4899" />;
      case 'property':
      case 'statement':
        return <span style={{ color: '#38bdf8', fontSize: '12px' }}>✦</span>;
      default:
        return <Variable size={13} color="#10b981" />;
    }
  };

  // Check if a line has an active diagnostic
  const getLineDiagnostic = (lineNum: number) => {
    return diagnostics.find((d) => d.from_line === lineNum);
  };

  return (
    <div
      ref={containerRef}
      style={{
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        width: '100%',
        backgroundColor: 'var(--bg-cell)',
        borderRadius: '6px',
        border: '1px solid var(--border-main)',
        overflow: 'visible',
      }}
    >
      <div style={{ display: 'flex', width: '100%', position: 'relative' }}>
        {/* 1. Left Line Number Gutter */}
        <div
          ref={gutterRef}
          style={{
            width: '44px',
            padding: '10px 0',
            backgroundColor: 'var(--bg-cell-gutter)',
            borderRight: '1px solid var(--border-main)',
            color: 'var(--text-muted)',
            fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
            fontSize: '12.5px',
            lineHeight: '21px',
            textAlign: 'right',
            userSelect: 'none',
            flexShrink: 0,
            overflowY: 'hidden',
            height: liveHeight ? `${liveHeight}px` : undefined,
            minHeight: liveHeight ? `${liveHeight}px` : `${Math.max(68, lines.length * 21 + 20)}px`,
            maxHeight: liveHeight ? `${liveHeight}px` : undefined,
          }}
        >
          {lines.map((_, i) => {
            const lineNum = i + 1;
            const diag = getLineDiagnostic(lineNum);
            return (
              <div
                key={lineNum}
                style={{
                  paddingRight: '10px',
                  height: '21px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'flex-end',
                  gap: '4px',
                  color: diag ? '#ef4444' : 'var(--text-muted)',
                  fontWeight: diag ? 700 : 400,
                }}
                title={diag ? diag.message : undefined}
              >
                {diag && <span style={{ width: '5px', height: '5px', borderRadius: '50%', backgroundColor: '#ef4444' }} />}
                {lineNum}
              </div>
            );
          })}
        </div>

        {/* 2. Main Editor Area */}
        <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
          {/* Underlying Diagnostics Underline Layer */}
          <div
            ref={diagnosticLayerRef}
            aria-hidden="true"
            style={{
              position: 'absolute',
              inset: 0,
              padding: '10px 14px',
              fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
              fontSize: '13.5px',
              lineHeight: '21px',
              pointerEvents: 'none',
              whiteSpace: 'pre',
              zIndex: 1,
              color: 'transparent',
              overflowY: 'hidden',
              overflowX: 'hidden',
              height: liveHeight ? `${liveHeight}px` : undefined,
              maxHeight: liveHeight ? `${liveHeight}px` : undefined,
            }}
          >
            {lines.map((lineStr, lineIdx) => {
              const lineNum = lineIdx + 1;
              const diag = getLineDiagnostic(lineNum);

              if (!diag) {
                return (
                  <div key={lineIdx} style={{ height: '21px' }}>
                    {lineStr || ' '}
                  </div>
                );
              }

              const fromCol = Math.max(0, Math.min(lineStr.length, diag.from_col));
              const toCol = Math.max(fromCol + 1, Math.min(lineStr.length, diag.to_col));

              const before = lineStr.substring(0, fromCol);
              const errorPart = lineStr.substring(fromCol, toCol) || lineStr.slice(-1) || ' ';
              const after = lineStr.substring(toCol);

              return (
                <div key={lineIdx} style={{ height: '21px' }}>
                  <span>{before}</span>
                  <span
                    style={{
                      textDecoration: 'underline wavy #ef4444',
                      textDecorationSkipInk: 'none',
                      backgroundColor: 'rgba(239, 68, 68, 0.15)',
                      borderRadius: '2px',
                    }}
                  >
                    {errorPart}
                  </span>
                  <span>{after}</span>
                </div>
              );
            })}
          </div>

          {/* Real Editor Textarea */}
          <textarea
            ref={(el) => {
              (textareaRef as React.MutableRefObject<HTMLTextAreaElement | null>).current = el;
              if (editorRef) editorRef(el);
            }}
            data-testid="code-cell-editor"
            className="code-font code-cell-editor"
            value={code}
            onFocus={onFocus}
            onChange={handleInput}
            onInput={handleInput}
            onClick={handleClick}
            onKeyDown={handleKeyDown}
            onScroll={handleScroll}
            placeholder={placeholder}
            readOnly={readOnly}
            spellCheck={false}
            autoComplete="off"
            autoCorrect="off"
            autoCapitalize="off"
            data-gramm="false"
            style={{
              width: '100%',
              height: liveHeight ? `${liveHeight}px` : undefined,
              minHeight: liveHeight ? `${liveHeight}px` : `${Math.max(68, lines.length * 21 + 20)}px`,
              maxHeight: liveHeight ? `${liveHeight}px` : undefined,
              backgroundColor: 'transparent',
              border: 'none',
              outline: 'none',
              color: 'var(--code-text)',
              fontSize: '13.5px',
              fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
              lineHeight: '21px',
              padding: '10px 14px',
              resize: 'none',
              whiteSpace: 'pre',
              overflowX: 'auto',
              overflowY: liveHeight ? 'auto' : 'hidden',
              position: 'relative',
              zIndex: 2,
              caretColor: 'var(--border-accent)',
            }}
          />

          {/* Hover Diagnostic Tooltip */}
          {diagnostics.length > 0 && (
            <div
              data-testid="diagnostic-badge"
              style={{
                position: 'absolute',
                right: '12px',
                bottom: '8px',
                zIndex: 3,
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                borderRadius: '5px',
                padding: '3px 8px',
                fontSize: '11px',
                color: '#ef4444',
                pointerEvents: 'none',
              }}
            >
              <AlertTriangle size={12} color="#ef4444" />
              <span>{diagnostics[0].message}</span>
            </div>
          )}
        </div>
      </div>

      {/* 3. Draggable vertical resize handle */}
      <div
        data-testid="cell-resize-handle"
        onMouseDown={handleResizeMouseDown}
        onDoubleClick={handleResetHeight}
        style={{
          height: '10px',
          cursor: 'ns-resize',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: isResizing ? 'rgba(59, 130, 246, 0.2)' : 'transparent',
          borderTop: '1px solid var(--border-main)',
          userSelect: 'none',
          width: '100%',
          transition: 'background-color 0.15s ease',
        }}
        title="Drag up/down to resize code cell. Double-click to auto-fit."
      >
        <div
          style={{
            width: '36px',
            height: '4px',
            borderRadius: '2px',
            backgroundColor: isResizing ? 'var(--border-accent)' : 'var(--border-secondary)',
          }}
        />
      </div>

      {/* 4. Floating Signature Help Tooltip */}
      {activeSignature && (
        <div
          ref={signatureRef}
          data-testid="signature-help-tooltip"
          style={{
            position: 'absolute',
            top: `${signaturePos.top}px`,
            left: `${signaturePos.left}px`,
            transform: signaturePos.placement === 'above' ? 'translateY(-100%)' : 'none',
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border-accent)',
            borderRadius: '6px',
            padding: '6px 12px',
            zIndex: 1001,
            boxShadow: '0 10px 25px rgba(0,0,0,0.3)',
            fontSize: '12px',
            fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
            color: 'var(--text-main)',
            maxWidth: '480px',
            pointerEvents: 'none',
          }}
        >
          {renderSignatureHelp(activeSignature)}
          {activeSignature.docstring && (
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '4px', whiteSpace: 'pre-wrap', maxHeight: '100px', overflowY: 'auto' }}>
              {activeSignature.docstring}
            </div>
          )}
        </div>
      )}

      {/* 5. Google Colab-style Autocomplete Dropdown */}
      {isDropdownOpen && completions.length > 0 && (
        <div
          ref={dropdownRef}
          data-testid="autocomplete-dropdown"
          role="dialog"
          aria-label="Code Suggestions"
          style={{
            position: 'absolute',
            top: `${dropdownPos.top}px`,
            left: `${dropdownPos.left}px`,
            transform: dropdownPos.placement === 'above' ? 'translateY(-100%)' : 'none',
            width: '320px',
            maxHeight: '260px',
            backgroundColor: 'var(--dropdown-bg)',
            border: '1px solid var(--dropdown-border)',
            borderRadius: '8px',
            boxShadow: '0 20px 40px rgba(0, 0, 0, 0.25)',
            zIndex: 1000,
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          {/* Header indicator */}
          <div
            style={{
              padding: '5px 10px',
              backgroundColor: 'var(--dropdown-header-bg)',
              borderBottom: '1px solid var(--border-main)',
              fontSize: '10.5px',
              color: 'var(--text-muted)',
              fontWeight: 600,
              display: 'flex',
              justifyContent: 'space-between',
              userSelect: 'none',
            }}
          >
            <span>SUGGESTIONS ({completions.length})</span>
            <span>Tab / ↵ to insert</span>
          </div>

          {/* Completion List */}
          <div
            ref={listRef}
            role="listbox"
            tabIndex={-1}
            style={{
              overflowY: 'auto',
              maxHeight: '220px',
              overscrollBehavior: 'contain',
            }}
          >
            {completions.map((item, idx) => {
              const isSelected = idx === selectedIndex;
              return (
                <div
                  key={`${item.label}-${idx}`}
                  role="option"
                  aria-selected={isSelected}
                  data-testid={`completion-item-${item.label}`}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    acceptCompletion(item);
                  }}
                  onClick={(e) => {
                    e.preventDefault();
                    acceptCompletion(item);
                  }}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '6px 10px',
                    backgroundColor: isSelected ? 'var(--dropdown-item-selected)' : 'transparent',
                    cursor: 'pointer',
                    fontSize: '12.5px',
                    fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
                    borderBottom: '1px solid var(--border-main)',
                    transition: 'background-color 0.05s ease',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
                    {renderItemIcon(item.type)}
                    <span
                      style={{
                        color: isSelected ? 'var(--dropdown-item-selected-text)' : 'var(--text-main)',
                        fontWeight: isSelected ? 600 : 400,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {item.label}
                    </span>
                  </div>
                  <span
                    style={{
                      fontSize: '11px',
                      color: isSelected ? 'var(--dropdown-item-selected-text)' : 'var(--text-muted)',
                      flexShrink: 0,
                      marginLeft: '8px',
                    }}
                  >
                    {item.type}
                  </span>
                </div>
              );
            })}
          </div>

          {/* Selected Item Documentation Preview Footer */}
          {completions[selectedIndex]?.documentation && (
            <div
              style={{
                padding: '6px 10px',
                backgroundColor: 'var(--dropdown-header-bg)',
                borderTop: '1px solid var(--border-main)',
                fontSize: '11px',
                color: 'var(--text-secondary)',
                maxHeight: '60px',
                overflowY: 'auto',
                whiteSpace: 'pre-wrap',
                overscrollBehavior: 'contain',
              }}
            >
              {completions[selectedIndex].documentation}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
