// frontend/src/store/__tests__/themeStore.test.ts
import { describe, it, expect, beforeEach } from 'vitest';
import { useThemeStore } from '../themeStore';

describe('themeStore', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove('dark');
  });

  it('initializes with theme state and toggles theme', () => {
    const initialDark = useThemeStore.getState().isDark;
    expect(typeof initialDark).toBe('boolean');

    useThemeStore.getState().toggleTheme();
    const newDark = useThemeStore.getState().isDark;
    expect(newDark).toBe(!initialDark);
    expect(localStorage.getItem('adaptivecloud_theme')).toBe(newDark ? 'dark' : 'light');

    useThemeStore.getState().setTheme(true);
    expect(useThemeStore.getState().isDark).toBe(true);
    expect(document.documentElement.classList.contains('dark')).toBe(true);

    useThemeStore.getState().setTheme(false);
    expect(useThemeStore.getState().isDark).toBe(false);
    expect(document.documentElement.classList.contains('dark')).toBe(false);
  });
});
