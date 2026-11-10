import { reactive } from 'vue'

export const toasts = reactive({ items: [] })
let n = 0

export function toast(message, kind = 'info', ms = 4200) {
  const id = ++n
  toasts.items.push({ id, message, kind })
  setTimeout(() => dismiss(id), ms)
}
export const dismiss = (id) => {
  toasts.items = toasts.items.filter((t) => t.id !== id)
}
