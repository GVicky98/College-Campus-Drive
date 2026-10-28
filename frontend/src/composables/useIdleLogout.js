import { onBeforeUnmount, onMounted } from 'vue'

/** Calls `onIdle` after `minutes()` without mouse, keyboard, scroll or touch activity. */
export function useIdleLogout(minutes, onIdle) {
  let timer
  const reset = () => {
    clearTimeout(timer)
    timer = setTimeout(onIdle, Math.max(5, minutes() || 60) * 60000)
  }
  const events = ['mousemove', 'keydown', 'scroll', 'touchstart', 'click']
  onMounted(() => { events.forEach((e) => window.addEventListener(e, reset, { passive: true })); reset() })
  onBeforeUnmount(() => { clearTimeout(timer); events.forEach((e) => window.removeEventListener(e, reset)) })
  return { reset }
}
