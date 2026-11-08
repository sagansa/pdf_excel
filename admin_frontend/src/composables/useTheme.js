import { computed, ref } from 'vue';

const STORAGE_KEY = 'statementx-theme';
const VALID_THEMES = ['light', 'dark', 'system'];
const theme = ref('system'); // user preference: 'light' | 'dark' | 'system'
let initialized = false;
let mediaQuery = null;

const getSystemTheme = () => {
  if (typeof window === 'undefined') return 'light';
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
};

const resolveTheme = (preference) => {
  if (preference === 'system') return getSystemTheme();
  return preference === 'dark' ? 'dark' : 'light';
};

const applyTheme = (appliedTheme) => {
  if (typeof document === 'undefined') return;

  document.documentElement.classList.toggle('dark', appliedTheme === 'dark');
  document.documentElement.dataset.theme = appliedTheme;
};

const getPreferredTheme = () => {
  if (typeof window === 'undefined') return 'system';

  const storedTheme = window.localStorage.getItem(STORAGE_KEY);
  return VALID_THEMES.includes(storedTheme) ? storedTheme : 'system';
};

const applyFromPreference = () => {
  applyTheme(resolveTheme(theme.value));
};

const handleSystemThemeChange = () => {
  if (theme.value === 'system') {
    applyFromPreference();
  }
};

export const initializeTheme = () => {
  if (initialized || typeof window === 'undefined') return;

  theme.value = getPreferredTheme();
  applyFromPreference();

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
    theme.value = VALID_THEMES.includes(nextTheme) ? nextTheme : 'system';

    if (typeof window !== 'undefined') {
      window.localStorage.setItem(STORAGE_KEY, theme.value);
    }

    applyFromPreference();
  };

  return {
    theme,
    isDark: computed(() => resolveTheme(theme.value) === 'dark'),
    setTheme
  };
};
