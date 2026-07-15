import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

export type ThemePreference = 'light' | 'dark' | 'system';

const STORAGE_KEY = 'homework-checker-theme';

function readStored(): ThemePreference {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    if (v === 'light' || v === 'dark' || v === 'system') return v;
  } catch {
    /* ignore */
  }
  return 'system';
}

function systemIsDark(): boolean {
  return window.matchMedia('(prefers-color-scheme: dark)').matches;
}

export function resolveTheme(pref: ThemePreference): 'light' | 'dark' {
  if (pref === 'dark') return 'dark';
  if (pref === 'light') return 'light';
  return systemIsDark() ? 'dark' : 'light';
}

type ThemeContextValue = {
  preference: ThemePreference;
  setPreference: (p: ThemePreference) => void;
  resolved: 'light' | 'dark';
  cyclePreference: () => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [preference, setPreference] = useState<ThemePreference>(readStored);
  const [systemTick, setSystemTick] = useState(0);

  const resolved = useMemo(
    () => resolveTheme(preference),
    [preference, systemTick],
  );

  const applyClass = useCallback((mode: 'light' | 'dark') => {
    document.documentElement.classList.toggle('dark', mode === 'dark');
  }, []);

  useEffect(() => {
    applyClass(resolved);
    try {
      localStorage.setItem(STORAGE_KEY, preference);
    } catch {
      /* ignore */
    }
  }, [preference, resolved, applyClass]);

  useEffect(() => {
    if (preference !== 'system') return;
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const onChange = () => setSystemTick((n) => n + 1);
    mq.addEventListener('change', onChange);
    return () => mq.removeEventListener('change', onChange);
  }, [preference]);

  const cyclePreference = useCallback(() => {
    setPreference((p) => {
      if (p === 'system') return 'light';
      if (p === 'light') return 'dark';
      return 'system';
    });
  }, []);

  const value = useMemo(
    () => ({
      preference,
      setPreference,
      resolved,
      cyclePreference,
    }),
    [preference, resolved, cyclePreference],
  );

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider');
  return ctx;
}
