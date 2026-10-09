import React, { useState } from 'react';
import { Play, Plus, Trash2, ArrowUp, ArrowDown, FileText, AlertTriangle, Eye, Edit3 } from 'lucide-react';
import { NotebookCell, KernelOutput } from '../types';

interface NotebookEditorProps {
  cells: NotebookCell[];
  onUpdateCellSource: (cellId: string, newSource: string) => void;
  onRunCell: (cellId: string) => void;
  onAddCell: (index: number, cellType: 'code' | 'markdown') => void;
  onDeleteCell: (cellId: string) => void;
  onMoveCell: (cellId: string, direction: 'up' | 'down') => void;
  activeCellId: string | null;
  onSelectCell: (cellId: string) => void;
}

export const NotebookEditor: React.FC<NotebookEditorProps> = ({
  cells,
  onUpdateCellSource,
  onRunCell,
  onAddCell,
  onDeleteCell,
  onMoveCell,
  activeCellId,
  onSelectCell,
}) => {
  const [markdownPreviews, setMarkdownPreviews] = useState<Record<string, boolean>>({});

  const toggleMarkdownPreview = (cellId: string) => {
    setMarkdownPreviews(prev => ({ ...prev, [cellId]: !prev[cellId] }));
  };

  const renderOutput = (output: KernelOutput, idx: number) => {
    if (output.output_type === 'stream') {
      const isErr = output.name === 'stderr';
      return (
        <pre
          key={idx}
          style={{
            color: isErr ? '#f87171' : '#e2e8f0',
            fontSize: '13px',
            lineHeight: 1.5,
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            margin: '4px 0',
          }}
        >
          {output.text}
        </pre>
      );
    }

    if (output.output_type === 'display_data' || output.output_type === 'execute_result') {
      const data = output.data || {};
      if (data['image/png']) {
        return (
          <div key={idx} style={{ margin: '8px 0', borderRadius: '4px', overflow: 'hidden', backgroundColor: '#ffffff', display: 'inline-block', padding: '8px' }}>
            <img src={`data:image/png;base64,${data['image/png']}`} alt="Kernel Plot" style={{ maxWidth: '100%', height: 'auto', display: 'block' }} />
          </div>
        );
      }
      if (data['text/html']) {
        return (
          <div
            key={idx}
            style={{ margin: '8px 0', overflowX: 'auto', color: '#e2e8f0' }}
            dangerouslySetInnerHTML={{ __html: data['text/html'] }}
          />
        );
      }
      if (data['text/plain']) {
        return (
          <pre
            key={idx}
            style={{ color: '#38bdf8', fontSize: '13px', lineHeight: 1.5, whiteSpace: 'pre-wrap', wordBreak: 'break-word', margin: '4px 0' }}
          >
            {data['text/plain']}
          </pre>
        );
      }
    }

    if (output.output_type === 'error') {
      return (
        <div key={idx} style={{ margin: '6px 0', padding: '10px', backgroundColor: '#450a0a', borderLeft: '3px solid #ef4444', borderRadius: '4px' }}>
          <div style={{ color: '#f87171', fontWeight: 600, fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <AlertTriangle size={15} />
            {output.ename}: {output.evalue}
          </div>
          {output.traceback && output.traceback.length > 0 && (
            <pre style={{ color: '#fca5a5', fontSize: '12px', marginTop: '6px', whiteSpace: 'pre-wrap', overflowX: 'auto' }}>
              {output.traceback.join('\n')}
            </pre>
          )}
        </div>
      );
    }

    return null;
  };

  return (
    <div style={{
      flex: 1,
      height: 'calc(100vh - 56px)',
      overflowY: 'auto',
      backgroundColor: '#090d16',
      padding: '24px 32px 120px 32px'
    }}>
      <div style={{ maxWidth: '920px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {cells.map((cell, index) => {
          const isActive = cell.id === activeCellId;
          const isMarkdownPreview = cell.cell_type === 'markdown' && !!markdownPreviews[cell.id];

          return (
            <div
              key={cell.id}
              onClick={() => onSelectCell(cell.id)}
              className={`cell-wrapper ${isActive ? 'active' : ''}`}
              style={{
                borderRadius: '8px',
                border: '1px solid #1e293b',
                backgroundColor: '#0f172a',
                overflow: 'hidden'
              }}
            >
              {/* Cell Header Toolbar */}
              <div style={{
                height: '36px',
                backgroundColor: '#131d31',
                borderBottom: '1px solid #1e293b',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0 12px'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  {cell.cell_type === 'code' ? (
                    <span style={{ fontSize: '12px', fontWeight: 600, color: '#3b82f6', width: '36px' }}>
                      {cell.is_running ? '[*]' : cell.execution_count ? `[${cell.execution_count}]` : '[ ]'}
                    </span>
                  ) : (
                    <span style={{ fontSize: '12px', color: '#94a3b8', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <FileText size={13} /> Markdown
                    </span>
                  )}
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  {cell.cell_type === 'code' ? (
                    <button
                      onClick={(e) => { e.stopPropagation(); onRunCell(cell.id); }}
                      style={{
                        padding: '4px 8px',
                        backgroundColor: '#2563eb',
                        border: 'none',
                        borderRadius: '4px',
                        color: '#ffffff',
                        fontSize: '11px',
                        fontWeight: 600,
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                        cursor: 'pointer'
                      }}
                      title="Run Cell (Shift+Enter)"
                    >
                      <Play size={12} fill="#ffffff" /> Run
                    </button>
                  ) : (
                    <button
                      onClick={(e) => { e.stopPropagation(); toggleMarkdownPreview(cell.id); }}
                      style={{
                        padding: '4px 8px',
                        backgroundColor: '#1e293b',
                        border: '1px solid #334155',
                        borderRadius: '4px',
                        color: '#cbd5e1',
                        fontSize: '11px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px'
                      }}
                    >
                      {isMarkdownPreview ? <><Edit3 size={12} /> Edit</> : <><Eye size={12} /> Preview</>}
                    </button>
                  )}

                  <button
                    onClick={(e) => { e.stopPropagation(); onMoveCell(cell.id, 'up'); }}
                    disabled={index === 0}
                    style={{ backgroundColor: 'transparent', border: 'none', color: '#64748b', cursor: index === 0 ? 'default' : 'pointer', padding: '4px' }}
                    title="Move Cell Up"
                  >
                    <ArrowUp size={14} />
                  </button>

                  <button
                    onClick={(e) => { e.stopPropagation(); onMoveCell(cell.id, 'down'); }}
                    disabled={index === cells.length - 1}
                    style={{ backgroundColor: 'transparent', border: 'none', color: '#64748b', cursor: index === cells.length - 1 ? 'default' : 'pointer', padding: '4px' }}
                    title="Move Cell Down"
                  >
                    <ArrowDown size={14} />
                  </button>

                  <button
                    onClick={(e) => { e.stopPropagation(); onDeleteCell(cell.id); }}
                    style={{ backgroundColor: 'transparent', border: 'none', color: '#ef4444', cursor: 'pointer', padding: '4px' }}
                    title="Delete Cell"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>

              {/* Cell Input Area */}
              <div style={{ padding: '12px', backgroundColor: '#0b1120' }}>
                {cell.cell_type === 'markdown' && isMarkdownPreview ? (
                  <div style={{ color: '#e2e8f0', fontSize: '14px', lineHeight: 1.6, minHeight: '36px' }}>
                    {cell.source.split('\n').map((line, i) => {
                      if (line.startsWith('# ')) return <h1 key={i} style={{ fontSize: '20px', fontWeight: 700, margin: '8px 0', color: '#38bdf8' }}>{line.slice(2)}</h1>;
                      if (line.startsWith('## ')) return <h2 key={i} style={{ fontSize: '17px', fontWeight: 600, margin: '6px 0', color: '#60a5fa' }}>{line.slice(3)}</h2>;
                      return <p key={i} style={{ margin: '4px 0' }}>{line}</p>;
                    })}
                  </div>
                ) : (
                  <textarea
                    className="code-font"
                    value={cell.source}
                    onChange={(e) => onUpdateCellSource(cell.id, e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && e.shiftKey) {
                        e.preventDefault();
                        onRunCell(cell.id);
                      }
                    }}
                    placeholder={cell.cell_type === 'code' ? '# Write Python code here...' : 'Write Markdown text here...'}
                    style={{
                      width: '100%',
                      minHeight: '70px',
                      backgroundColor: 'transparent',
                      border: 'none',
                      outline: 'none',
                      color: cell.cell_type === 'code' ? '#f1f5f9' : '#cbd5e1',
                      fontSize: '13.5px',
                      lineHeight: 1.6,
                      resize: 'vertical'
                    }}
                  />
                )}
              </div>

              {/* Cell Output Area */}
              {cell.outputs && cell.outputs.length > 0 && (
                <div style={{
                  padding: '12px',
                  backgroundColor: '#090d16',
                  borderTop: '1px solid #1e293b'
                }}>
                  {cell.outputs.map((out, oIdx) => renderOutput(out, oIdx))}
                </div>
              )}
            </div>
          );
        })}

        {/* Bottom Cell Inserter */}
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          gap: '12px',
          marginTop: '16px'
        }}>
          <button
            onClick={() => onAddCell(cells.length, 'code')}
            style={{
              padding: '8px 16px',
              backgroundColor: '#1e293b',
              color: '#38bdf8',
              border: '1px solid #334155',
              borderRadius: '6px',
              fontSize: '13px',
              fontWeight: 500,
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              cursor: 'pointer'
            }}
          >
            <Plus size={15} /> Add Code Cell
          </button>
          <button
            onClick={() => onAddCell(cells.length, 'markdown')}
            style={{
              padding: '8px 16px',
              backgroundColor: '#1e293b',
              color: '#94a3b8',
              border: '1px solid #334155',
              borderRadius: '6px',
              fontSize: '13px',
              fontWeight: 500,
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              cursor: 'pointer'
            }}
          >
            <Plus size={15} /> Add Text Cell
          </button>
        </div>
      </div>
    </div>
  );
};
