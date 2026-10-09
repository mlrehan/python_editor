import React, { useState } from 'react';
import { Sparkles, Database, Activity, Send, Copy } from 'lucide-react';

interface RightPanelProps {
  onInsertCodeSnippet: (code: string) => void;
}

export const RightPanel: React.FC<RightPanelProps> = ({ onInsertCodeSnippet }) => {
  const [activeTab, setActiveTab] = useState<'variables' | 'ai' | 'metrics'>('ai');
  const [messages, setMessages] = useState<Array<{ sender: 'user' | 'assistant'; text: string; code?: string }>>([
    {
      sender: 'assistant',
      text: 'Hello! I am your Python Cloud Studio Assistant. Ask me to explain code, fix exceptions, or generate Pandas / NumPy snippets.',
    },
  ]);
  const [inputPrompt, setInputPrompt] = useState('');
  const [isTyping, setIsTyping] = useState(false);

  const handleSendAI = () => {
    if (!inputPrompt.trim()) return;
    const userMsg = inputPrompt;
    setMessages(prev => [...prev, { sender: 'user', text: userMsg }]);
    setInputPrompt('');
    setIsTyping(true);

    // Contextual AI assistant response
    setTimeout(() => {
      let replyText = "Here is an optimized Python approach:";
      let snippet = `import pandas as pd\n\n# Create sample dataset\ndf = pd.DataFrame({\n    'category': ['A', 'B', 'A', 'C'],\n    'values': [10, 20, 15, 30]\n})\n\n# Aggregate sum by category\nsummary = df.groupby('category').sum()\nprint(summary)`;

      if (userMsg.toLowerCase().includes('plot') || userMsg.toLowerCase().includes('chart')) {
        replyText = "Here is how to create a high-resolution Matplotlib figure:";
        snippet = `import matplotlib.pyplot as plt\nimport numpy as np\n\nx = np.linspace(0, 10, 100)\ny = np.sin(x)\n\nplt.figure(figsize=(8, 4))\nplt.plot(x, y, color='#3b82f6', lw=2, label='sin(x)')\nplt.title('Sine Wave')\nplt.grid(True, alpha=0.3)\nplt.legend()\nplt.show()`;
      } else if (userMsg.toLowerCase().includes('error') || userMsg.toLowerCase().includes('exception')) {
        replyText = "To safely handle exceptions and debug issues in Python, use structured try/except blocks with logging:";
        snippet = `try:\n    value = int("invalid_num")\nexcept ValueError as e:\n    print(f"Handled parsing failure: {e}")`;
      }

      setMessages(prev => [...prev, { sender: 'assistant', text: replyText, code: snippet }]);
      setIsTyping(false);
    }, 600);
  };

  return (
    <aside style={{
      width: '320px',
      backgroundColor: '#0f172a',
      borderLeft: '1px solid #1e293b',
      display: 'flex',
      flexDirection: 'column',
      height: 'calc(100vh - 56px)'
    }}>
      {/* Tab Switcher */}
      <div style={{ display: 'flex', borderBottom: '1px solid #1e293b', backgroundColor: '#0b1120' }}>
        <button
          onClick={() => setActiveTab('ai')}
          style={{
            flex: 1,
            padding: '10px 0',
            backgroundColor: 'transparent',
            border: 'none',
            borderBottom: activeTab === 'ai' ? '2px solid #8b5cf6' : 'none',
            color: activeTab === 'ai' ? '#a78bfa' : '#64748b',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '6px',
            fontSize: '12px',
            fontWeight: 500,
            cursor: 'pointer'
          }}
        >
          <Sparkles size={14} /> AI Assistant
        </button>
        <button
          onClick={() => setActiveTab('variables')}
          style={{
            flex: 1,
            padding: '10px 0',
            backgroundColor: 'transparent',
            border: 'none',
            borderBottom: activeTab === 'variables' ? '2px solid #3b82f6' : 'none',
            color: activeTab === 'variables' ? '#3b82f6' : '#64748b',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '6px',
            fontSize: '12px',
            fontWeight: 500,
            cursor: 'pointer'
          }}
        >
          <Database size={14} /> Variables
        </button>
        <button
          onClick={() => setActiveTab('metrics')}
          style={{
            flex: 1,
            padding: '10px 0',
            backgroundColor: 'transparent',
            border: 'none',
            borderBottom: activeTab === 'metrics' ? '2px solid #10b981' : 'none',
            color: activeTab === 'metrics' ? '#10b981' : '#64748b',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '6px',
            fontSize: '12px',
            fontWeight: 500,
            cursor: 'pointer'
          }}
        >
          <Activity size={14} /> Metrics
        </button>
      </div>

      {/* Tab Content */}
      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
        {activeTab === 'ai' && (
          <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            {/* Messages */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '12px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {messages.map((m, idx) => (
                <div key={idx} style={{
                  padding: '10px 12px',
                  borderRadius: '8px',
                  backgroundColor: m.sender === 'assistant' ? '#1e1b4b' : '#1e293b',
                  border: m.sender === 'assistant' ? '1px solid #4338ca' : '1px solid #334155',
                  fontSize: '13px',
                  lineHeight: 1.5,
                  color: '#e2e8f0'
                }}>
                  <div style={{ fontWeight: 600, fontSize: '11px', color: m.sender === 'assistant' ? '#a78bfa' : '#60a5fa', marginBottom: '4px' }}>
                    {m.sender === 'assistant' ? 'AI Assistant' : 'You'}
                  </div>
                  <p>{m.text}</p>
                  {m.code && (
                    <div style={{ marginTop: '8px', backgroundColor: '#090d16', padding: '8px', borderRadius: '4px' }}>
                      <pre className="code-font" style={{ fontSize: '12px', color: '#38bdf8', overflowX: 'auto', whiteSpace: 'pre-wrap' }}>
                        {m.code}
                      </pre>
                      <button
                        onClick={() => onInsertCodeSnippet(m.code!)}
                        style={{
                          marginTop: '6px',
                          padding: '3px 8px',
                          backgroundColor: '#2563eb',
                          border: 'none',
                          borderRadius: '4px',
                          color: '#ffffff',
                          fontSize: '11px',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px'
                        }}
                      >
                        <Copy size={11} /> Insert in Notebook
                      </button>
                    </div>
                  )}
                </div>
              ))}
              {isTyping && <div style={{ fontSize: '12px', color: '#94a3b8' }}>AI is thinking...</div>}
            </div>

            {/* Input Box */}
            <div style={{ padding: '12px', borderTop: '1px solid #1e293b', display: 'flex', gap: '6px' }}>
              <input
                type="text"
                value={inputPrompt}
                onChange={(e) => setInputPrompt(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') handleSendAI(); }}
                placeholder="Ask Python question..."
                style={{
                  flex: 1,
                  padding: '8px 10px',
                  backgroundColor: '#1e293b',
                  border: '1px solid #334155',
                  borderRadius: '6px',
                  color: '#f8fafc',
                  fontSize: '13px',
                  outline: 'none'
                }}
              />
              <button
                onClick={handleSendAI}
                style={{
                  padding: '8px 12px',
                  backgroundColor: '#7c3aed',
                  border: 'none',
                  borderRadius: '6px',
                  color: '#ffffff',
                  cursor: 'pointer'
                }}
              >
                <Send size={14} />
              </button>
            </div>
          </div>
        )}

        {activeTab === 'variables' && (
          <div style={{ padding: '16px', color: '#94a3b8', fontSize: '13px' }}>
            <p style={{ fontWeight: 600, color: '#f8fafc', marginBottom: '8px' }}>Active Kernel Scope</p>
            <p>Run code cells to inspect local variables, dataframes, and arrays in real-time memory.</p>
          </div>
        )}

        {activeTab === 'metrics' && (
          <div style={{ padding: '16px', color: '#94a3b8', fontSize: '13px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div>
              <div style={{ fontSize: '11px', textTransform: 'uppercase', color: '#64748b' }}>CPU Quota</div>
              <div style={{ fontSize: '16px', fontWeight: 600, color: '#f8fafc' }}>2.0 Cores (Standard)</div>
            </div>
            <div>
              <div style={{ fontSize: '11px', textTransform: 'uppercase', color: '#64748b' }}>Memory Limit</div>
              <div style={{ fontSize: '16px', fontWeight: 600, color: '#f8fafc' }}>4.0 GB RAM</div>
            </div>
            <div>
              <div style={{ fontSize: '11px', textTransform: 'uppercase', color: '#64748b' }}>Disk Quota</div>
              <div style={{ fontSize: '16px', fontWeight: 600, color: '#f8fafc' }}>10.0 GB Persistent</div>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
};
