import type { ChatCompletionTool } from "openai/resources"
import type { Page } from "playwright"

function isSafeNavigateUrl(url: string): boolean {
  try {
    const u = new URL(url)
    if (u.protocol !== "https:" && u.protocol !== "http:") return false
    const h = u.hostname.toLowerCase()
    if (h === "localhost" || h === "127.0.0.1" || h === "::1") return false
    const ipv4 = h.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/)
    if (ipv4) {
      const [, a, b] = ipv4.map(Number)
      if (a === 0) return false
      if (a === 10) return false
      if (a === 127) return false
      if (a === 169 && b === 254) return false
      if (a === 172 && b >= 16 && b <= 31) return false
      if (a === 192 && b === 168) return false
    }
    return true
  } catch { return false }
}

export const BROWSER_TOOLS: ChatCompletionTool[] = [
  {
    type: "function",
    function: {
      name: "navigate",
      description: "Navigate to a URL. Returns page title, HTTP status code, and final URL after redirects.",
      parameters: {
        type: "object",
        properties: {
          url: { type: "string", description: "The URL to navigate to" },
        },
        required: ["url"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "get_page_content",
      description: "Get the current page's visible text (up to 3000 chars), h1-h3 headings, and top 50 links.",
      parameters: {
        type: "object",
        properties: {},
        required: [],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "click_element",
      description: "Click an element by CSS selector or visible text. Returns success and new URL if navigation occurred.",
      parameters: {
        type: "object",
        properties: {
          selectorOrText: { type: "string", description: "CSS selector or visible text of the element to click" },
        },
        required: ["selectorOrText"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "fill_field",
      description: "Type a value into an input field identified by CSS selector.",
      parameters: {
        type: "object",
        properties: {
          selector: { type: "string", description: "CSS selector for the input field" },
          value: { type: "string", description: "Value to type into the field" },
        },
        required: ["selector", "value"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "get_forms",
      description: "Get all forms on the current page with their action URLs and field names/types.",
      parameters: {
        type: "object",
        properties: {},
        required: [],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "detect_blocking",
      description: "Check the current page for bot-blocking: CAPTCHA widgets, Cloudflare challenges, suspicious status codes.",
      parameters: {
        type: "object",
        properties: {},
        required: [],
      },
    },
  },
]

export async function executeTool(
  name: string,
  input: Record<string, unknown>,
  page: Page
): Promise<unknown> {
  switch (name) {
    case "navigate": {
      const targetUrl = input.url as string
      if (!isSafeNavigateUrl(targetUrl)) return { error: "URL rejected: not a safe public URL" }
      const response = await page.goto(targetUrl, { waitUntil: "domcontentloaded", timeout: 10000 }).catch(() => null)
      return {
        title: await page.title().catch(() => ""),
        statusCode: response?.status() ?? null,
        finalUrl: page.url(),
      }
    }

    case "get_page_content": {
      const text = await page.evaluate(() => document.body?.innerText ?? "").catch(() => "")
      const headings = await page.evaluate(() =>
        Array.from(document.querySelectorAll("h1, h2, h3")).slice(0, 10).map(el => el.textContent?.trim() ?? "")
      ).catch(() => [] as string[])
      const links = await page.evaluate(() =>
        Array.from(document.querySelectorAll("a[href]")).slice(0, 50).map(el => ({
          text: (el as HTMLAnchorElement).textContent?.trim().slice(0, 60) ?? "",
          href: (el as HTMLAnchorElement).href,
        }))
      ).catch(() => [] as { text: string; href: string }[])
      return { text: (text as string).slice(0, 3000), headings, links }
    }

    case "click_element": {
      const selectorOrText = input.selectorOrText as string
      try {
        await page.locator(selectorOrText).or(page.getByText(selectorOrText)).first().click({ timeout: 5000 })
        return { success: true, newUrl: page.url() }
      } catch {
        return { success: false, newUrl: page.url() }
      }
    }

    case "fill_field": {
      try {
        await page.fill(input.selector as string, input.value as string, { timeout: 5000 })
        return { success: true }
      } catch {
        return { success: false }
      }
    }

    case "get_forms": {
      const forms = await page.evaluate(() =>
        Array.from(document.querySelectorAll("form")).map(form => ({
          action: (form as HTMLFormElement).action ?? "",
          fields: Array.from(form.querySelectorAll("input, textarea, select")).map(el => ({
            name: (el as HTMLInputElement).name || (el as HTMLInputElement).id || "",
            type: (el as HTMLInputElement).type || el.tagName.toLowerCase(),
          })),
        }))
      ).catch(() => [] as { action: string; fields: { name: string; type: string }[] }[])
      return { forms }
    }

    case "detect_blocking": {
      const hasCaptcha = await page.evaluate(() => {
        const iframeSrc = document.querySelector("iframe")?.src ?? ""
        return iframeSrc.includes("hcaptcha") || iframeSrc.includes("recaptcha") ||
          !!document.querySelector(".h-captcha, .g-recaptcha, [data-sitekey]")
      }).catch(() => false)

      const hasCfChallenge = await page.evaluate(() =>
        document.title.includes("Just a moment") ||
        !!document.querySelector("#cf-challenge-running, #cf-error-details")
      ).catch(() => false)

      const botSignals = await page.evaluate(() => {
        const signals: string[] = []
        if (document.title.includes("Access denied")) signals.push("access-denied-title")
        if (document.title.includes("403")) signals.push("403-in-title")
        if (document.title.includes("Attention Required")) signals.push("attention-required-title")
        return signals
      }).catch(() => [] as string[])

      return { hasCaptcha, hasCfChallenge, botSignals }
    }

    default:
      return { error: `Unknown tool: ${name}` }
  }
}
