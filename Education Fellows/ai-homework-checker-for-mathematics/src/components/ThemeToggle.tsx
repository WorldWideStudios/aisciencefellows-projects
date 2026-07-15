import { Monitor, Moon, Sun } from 'lucide-react';
import { useTheme, type ThemePreference } from '../ThemeContext';

const labels: Record<ThemePreference, string> = {
  system: 'Theme: System',
  light: 'Theme: Light',
  dark: 'Theme: Dark',
};

export function ThemeToggle() {
  const { preference, cyclePreference } = useTheme();

  const Icon =
    preference === 'system' ? Monitor : preference === 'light' ? Sun : Moon;

  return (
    <button
      type="button"
      onClick={cyclePreference}
      title={labels[preference]}
      aria-label={labels[preference]}
      className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 shadow-sm transition-colors hover:bg-slate-50 hover:text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700 dark:hover:text-white"
    >
      <Icon size={18} strokeWidth={2} />
    </button>
  );
}
