export function normalizeUrl(input: string): { url: string; domain: string } {
  const withScheme = /^https?:\/\//i.test(input.trim()) ? input.trim() : `https://${input.trim()}`
  const parsed = new URL(withScheme)
  let domain = parsed.hostname.replace(/^www\./, "")
  const parts = domain.split(".")
  if (parts.length > 2) {
    domain = parts.slice(-2).join(".")
  }
  return { url: `${parsed.protocol}//${parsed.host}`, domain }
}
