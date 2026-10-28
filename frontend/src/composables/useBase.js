import { computed } from 'vue'
import { useRoute } from 'vue-router'

/** The current area prefix ('/student', '/faculty' or '/admin'), so one page can serve several roles. */
export function useBase() {
  const route = useRoute()
  return computed(() => '/' + (route.path.split('/')[1] || ''))
}
