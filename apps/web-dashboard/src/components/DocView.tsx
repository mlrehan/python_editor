import React from 'react';
import { tokenizePython, renderHighlightedLines } from '../utils/pythonSyntax';

/*
 * Structured Python documentation (from the backend's introspection: inspect.signature, type hints and
 * the parsed docstring). Used by the signature tooltip and the suggestion details panel. Only sections
 * the documentation actually contains are shown.
 */

export interface DocParam {
  name: string;
  kind?: string;
  type?: string | null;
  default?: string | null;
  description?: string | null;
}

export interface DocEntry {
  name?: string | null;
  type?: string | null;
  description?: string | null;
}

export interface PythonDoc {
  name: string;
  qualname?: string;
  kind?: string;
  signature?: string | null;
  summary?: string | null;
  description?: string | null;
  parameters?: DocParam[];
  returns?: DocEntry[];
  raises?: DocEntry[];
  examples?: string | null;
  notes?: string | null;
  see_also?: string[];
  has_docstring?: boolean;
}

// Inline reST/Markdown used in scientific docstrings: ``code``, `code`, :func:`name`
function renderInline(text: string): React.ReactNode[] {
  const out: React.ReactNode[] = [];
  const re = /:[\w:]+:`~?([^`]+)`|``([^`]+)``|`([^`]+)`|\*\*([^*]+)\*\*/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let key = 0;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    if (m[4] !== undefined) out.push(<strong key={key++}>{m[4]}</strong>);
    else out.push(<code key={key++} className="doc-code">{m[1] ?? m[2] ?? m[3]}</code>);
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

function Paragraphs({ text }: { text: string }) {
  return (
    <>
      {text.split(/\n\s*\n/).map((p, i) => (
        <p key={i} className="doc-p">
          {renderInline(p.replace(/\s*\n\s*/g, ' '))}
        </p>
      ))}
    </>
  );
}

function stripParam(name: string) {
  return name.replace(/^\*+/, '');
}

interface DocViewProps {
  doc: PythonDoc;
  /** Parameter being typed (highlighted and described first) */
  activeParam?: string | null;
  /** The signature line is rendered by the caller (with its own highlighting) */
  hideSignature?: boolean;
  compact?: boolean;
}

export const DocView: React.FC<DocViewProps> = ({ doc, activeParam, hideSignature, compact }) => {
  const params = doc.parameters || [];
  const active = activeParam ? params.find((p) => stripParam(p.name) === stripParam(activeParam)) : undefined;
  const returns = (doc.returns || []).filter((r) => r.type || r.description);
  const raises = (doc.raises || []).filter((r) => r.name || r.type || r.description);

  return (
    <div className={`doc-view${compact ? ' doc-view--compact' : ''}`} data-testid="doc-view">
      {!hideSignature && doc.signature && <div className="doc-signature">{doc.signature}</div>}

      {active && (
        <div className="doc-active-param" data-testid="doc-active-param">
          <code className="doc-param-name">{active.name}</code>
          {active.type && <span className="doc-param-type">: {active.type}</span>}
          {active.default != null && <span className="doc-param-default"> = {active.default}</span>}
          {active.description && <div className="doc-param-desc">{renderInline(active.description)}</div>}
        </div>
      )}

      {doc.summary ? (
        <div className="doc-summary">{renderInline(doc.summary)}</div>
      ) : (
        !doc.has_docstring && (
          <div className="doc-missing" data-testid="doc-missing">
            No documentation is available for {doc.name}.
          </div>
        )
      )}
      {!compact && doc.description && <Paragraphs text={doc.description} />}

      {params.length > 0 && (
        <section className="doc-section">
          <h4 className="doc-heading">Parameters</h4>
          <ul className="doc-params">
            {params.map((p) => (
              <li key={p.name} className={active && active.name === p.name ? 'is-active' : undefined}>
                <code className="doc-param-name">{p.name}</code>
                {p.type && <span className="doc-param-type">: {p.type}</span>}
                {p.default != null && <span className="doc-param-default"> = {p.default}</span>}
                {p.kind && p.kind !== 'positional or keyword' && <span className="doc-param-kind">{p.kind}</span>}
                {p.description && <div className="doc-param-desc">{renderInline(p.description)}</div>}
              </li>
            ))}
          </ul>
        </section>
      )}

      {returns.length > 0 && (
        <section className="doc-section">
          <h4 className="doc-heading">Returns</h4>
          <ul className="doc-params">
            {returns.map((r, i) => (
              <li key={i}>
                {r.type && <code className="doc-param-type">{r.type}</code>}
                {r.description && <div className="doc-param-desc">{renderInline(r.description)}</div>}
              </li>
            ))}
          </ul>
        </section>
      )}

      {!compact && raises.length > 0 && (
        <section className="doc-section">
          <h4 className="doc-heading">Raises</h4>
          <ul className="doc-params">
            {raises.map((r, i) => (
              <li key={i}>
                <code className="doc-param-type">{r.type || r.name}</code>
                {r.description && <div className="doc-param-desc">{renderInline(r.description)}</div>}
              </li>
            ))}
          </ul>
        </section>
      )}

      {doc.examples && (
        <section className="doc-section">
          <h4 className="doc-heading">Examples</h4>
          <pre className="doc-example code-font">{renderHighlightedLines(doc.examples, tokenizePython(doc.examples))}</pre>
        </section>
      )}

      {!compact && doc.notes && (
        <details className="doc-section">
          <summary className="doc-heading">Notes</summary>
          <Paragraphs text={doc.notes} />
        </details>
      )}

      {(doc.see_also || []).length > 0 && (
        <section className="doc-section">
          <h4 className="doc-heading">See also</h4>
          <div className="doc-see-also">
            {(doc.see_also || []).map((name) => (
              <code key={name} className="doc-code">
                {name}
              </code>
            ))}
          </div>
        </section>
      )}
    </div>
  );
};
