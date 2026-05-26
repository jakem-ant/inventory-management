import { ref, computed } from 'vue'

// Shared theme state (singleton pattern, same approach as useI18n/useFilters)
const savedTheme = localStorage.getItem('app-theme') || 'light'
const currentTheme = ref(savedTheme)

const applyTheme = (theme) => {
  document.documentElement.setAttribute('data-theme', theme)
}

// Apply on module load so the saved theme is active before components mount
applyTheme(savedTheme)

export function useTheme() {
  const isDark = computed(() => currentTheme.value === 'dark')

  const setTheme = (theme) => {
    if (theme !== 'light' && theme !== 'dark') return
    currentTheme.value = theme
    localStorage.setItem('app-theme', theme)
    applyTheme(theme)
  }

  const toggleTheme = () => {
    setTheme(isDark.value ? 'light' : 'dark')
  }

  return {
    currentTheme: computed(() => currentTheme.value),
    isDark,
    setTheme,
    toggleTheme
  }
}
