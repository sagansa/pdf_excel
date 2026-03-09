import { computed, ref } from 'vue';

const STORAGE_KEY = 'statementx-theme';
const theme = ref('light');
let initialized = false;
let mediaQuery = null;

const applyTheme = (nextTheme) => {
  if (typeof document === 'undefined') return;

  document.documentElement.classList.toggle('dark', nextTheme === 'dark');
  document.documentElement.dataset.theme = nextTheme;
};

const getPreferredTheme = () => {
  if (typeof window === 'undefined') return 'light';

  const storedTheme = window.localStorage.getItem(STORAGE_KEY);
  if (storedTheme === 'dark' || storedTheme === 'light') {
    return storedTheme;
  }

  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
};

const handleSystemThemeChange = (event) => {
  if (typeof window === 'undefined') return;
  if (window.localStorage.getItem(STORAGE_KEY)) return;

  theme.value = event.matches ? 'dark' : 'light';
  applyTheme(theme.value);
};

export const initializeTheme = () => {
  if (initialized || typeof window === 'undefined') return;

  theme.value = getPreferredTheme();
  applyTheme(theme.value);

  mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
  if (typeof mediaQuery.addEventListener === 'function') {
    mediaQuery.addEventListener('change', handleSystemThemeChange);
  } else if (typeof mediaQuery.addListener === 'function') {
    mediaQuery.addListener(handleSystemThemeChange);
  }

  initialized = true;
};

export const useTheme = () => {
  initializeTheme();

  const setTheme = (nextTheme) => {
    theme.value = nextTheme === 'dark' ? 'dark' : 'light';

    if (typeof window !== 'undefined') {
      window.localStorage.setItem(STORAGE_KEY, theme.value);
    }

    applyTheme(theme.value);
  };

  const toggleTheme = () => {
    setTheme(theme.value === 'dark' ? 'light' : 'dark');
  };

  return {
    theme,
    isDark: computed(() => theme.value === 'dark'),
    setTheme,
    toggleTheme
  };
};
