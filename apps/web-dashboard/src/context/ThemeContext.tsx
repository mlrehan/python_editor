import React, { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../services/api';

export type ThemeMode = 'system' | 'dark' | 'light';
export type EffectiveTheme = 'dark' | 'light';

interface ThemeContextType {
  themeMode: ThemeMode;
  effectiveTheme: EffectiveTheme;
  setThemeMode: (mode: ThemeMode) => void;
}

const ThemeContext = createContext<ThemeContextType>({
  themeMode: 'dark',
  effectiveTheme: 'dark',
  setThemeMode: () => {},
});

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [themeMode, setThemeModeState] = useState<ThemeMode>(() => {
    const saved = localStorage.getItem('pcs_theme') as ThemeMode;
    return saved === 'light' || saved === 'dark' || saved === 'system' ? saved : 'dark';
  });

  const getSystemTheme = (): EffectiveTheme => {
    if (typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
      return 'light';
    }
    return 'dark';
  };

  const [effectiveTheme, setEffectiveTheme] = useState<EffectiveTheme>(() => {
    if (themeMode === 'system') return getSystemTheme();
    return themeMode;
  });

  useEffect(() => {
    const resolveAndApply = () => {
      const resolved: EffectiveTheme = themeMode === 'system' ? getSystemTheme() : themeMode;
      setEffectiveTheme(resolved);
      document.documentElement.setAttribute('data-theme', resolved);
    };

    resolveAndApply();

    if (themeMode === 'system') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: light)');
      const listener = (e: MediaQueryListEvent) => {
        const newTheme: EffectiveTheme = e.matches ? 'light' : 'dark';
        setEffectiveTheme(newTheme);
        document.documentElement.setAttribute('data-theme', newTheme);
      };

      if (mediaQuery.addEventListener) {
        mediaQuery.addEventListener('change', listener);
        return () => mediaQuery.removeEventListener('change', listener);
      }
    }
  }, [themeMode]);

  const setThemeMode = (mode: ThemeMode) => {
    setThemeModeState(mode);
    localStorage.setItem('pcs_theme', mode);
    const resolved: EffectiveTheme = mode === 'system' ? getSystemTheme() : mode;
    setEffectiveTheme(resolved);
    document.documentElement.setAttribute('data-theme', resolved);

    // Sync with backend if logged in
    if (api.getToken()) {
      api.updateThemePreference(mode).catch((err) => {
        console.warn('Failed to sync theme preference to backend:', err);
      });
    }
  };

  return (
    <ThemeContext.Provider value={{ themeMode, effectiveTheme, setThemeMode }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => useContext(ThemeContext);

