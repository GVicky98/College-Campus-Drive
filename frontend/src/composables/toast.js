import { reactive } from 'vue'

// One global toast at a time, shown by <ToastHost /> in App.vue.
export const toastState = reactive({ message: '', tone: 'success', visible: false })
let timer

export function toast(message, tone = 'success') {
  toastState.message = message
  toastState.tone = tone
  toastState.visible = true
  clearTimeout(timer)
  timer = setTimeout(() => { toastState.visible = false }, 4500)
}

export const useToast = () => ({
  success: (m) => toast(m, 'success'),
  error: (m) => toast(m, 'error'),
  info: (m) => toast(m, 'info'),
  warning: (m) => toast(m, 'warning'),
})
