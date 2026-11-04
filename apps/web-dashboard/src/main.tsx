import React from 'react';
import ReactDOM from 'react-dom/client';
import { App } from './App';
import { ThemeProvider } from './context/ThemeContext';
// Fonts are bundled with the app: no external requests, and allowed by the Content-Security-Policy
import '@fontsource-variable/inter';
import '@fontsource-variable/jetbrains-mono';
import './editorSettings';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ThemeProvider>
      <App />
    </ThemeProvider>
  </React.StrictMode>
);
