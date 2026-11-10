// Tiny non-cryptographic hash (djb2). Demo only.
export function demoHash(text) {
  let h = 5381
  for (let i = 0; i < text.length; i++) h = ((h << 5) + h + text.charCodeAt(i)) | 0
  return 'h' + (h >>> 0).toString(16)
}
