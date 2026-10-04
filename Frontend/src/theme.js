import { useCallback, useState } from 'react'

const KEY = 'shipit.theme'

function current() {
  return document.documentElement.dataset.theme === 'light' ? 'light' : 'dark'
}

export function useTheme() {
  const [theme, setTheme] = useState(current)
  const toggle = useCallback(() => {
    const next = current() === 'dark' ? 'light' : 'dark'
    document.documentElement.dataset.theme = next
    try {
      localStorage.setItem(KEY, next)
    } catch {
      /* storage can be blocked */
    }
    setTheme(next)
  }, [])
  return [theme, toggle]
}
