import { BROWSER_TOOLS, executeTool } from "../tools"
import type { Page } from "playwright"

function makeMockPage(overrides: Partial<Record<string, unknown>> = {}): Page {
  return {
    goto: jest.fn().mockResolvedValue({ status: () => 200 }),
    title: jest.fn().mockResolvedValue("Test Page"),
    url: jest.fn().mockReturnValue("https://example.com"),
    evaluate: jest.fn().mockResolvedValue(""),
    locator: jest.fn().mockReturnValue({
      or: jest.fn().mockReturnThis(),
      first: jest.fn().mockReturnThis(),
      click: jest.fn().mockResolvedValue(undefined),
    }),
    getByText: jest.fn().mockReturnValue({
      or: jest.fn().mockReturnThis(),
      first: jest.fn().mockReturnThis(),
      click: jest.fn().mockResolvedValue(undefined),
    }),
    fill: jest.fn().mockResolvedValue(undefined),
    ...overrides,
  } as unknown as Page
}

describe("BROWSER_TOOLS schemas", () => {
  it("defines exactly 6 tools", () => {
    expect(BROWSER_TOOLS).toHaveLength(6)
  })

  it("each tool has type=function with name, description, and parameters with type=object", () => {
    for (const tool of BROWSER_TOOLS) {
      expect(tool.type).toBe("function")
      expect(typeof tool.function.name).toBe("string")
      expect(typeof tool.function.description).toBe("string")
      expect(tool.function.parameters).toBeDefined()
      expect((tool.function.parameters as { type: string }).type).toBe("object")
    }
  })

  it("defines the expected tool names in order", () => {
    const names = BROWSER_TOOLS.map(t => t.function.name)
    expect(names).toEqual([
      "navigate",
      "get_page_content",
      "click_element",
      "fill_field",
      "get_forms",
      "detect_blocking",
    ])
  })

  it("navigate tool requires a url property", () => {
    const navigate = BROWSER_TOOLS.find(t => t.function.name === "navigate")!
    const params = navigate.function.parameters as { properties: Record<string, unknown>; required: string[] }
    expect(params.properties).toHaveProperty("url")
    expect(params.required).toContain("url")
  })

  it("click_element tool requires selectorOrText", () => {
    const click = BROWSER_TOOLS.find(t => t.function.name === "click_element")!
    const params = click.function.parameters as { properties: Record<string, unknown>; required: string[] }
    expect(params.properties).toHaveProperty("selectorOrText")
    expect(params.required).toContain("selectorOrText")
  })
})

describe("executeTool", () => {
  it("navigate calls page.goto with the provided url and returns status + finalUrl", async () => {
    const page = makeMockPage()
    const result = await executeTool("navigate", { url: "https://example.com" }, page) as Record<string, unknown>
    expect(page.goto).toHaveBeenCalledWith("https://example.com", expect.objectContaining({ waitUntil: "domcontentloaded" }))
    expect(result.statusCode).toBe(200)
    expect(result.finalUrl).toBe("https://example.com")
  })

  it("navigate handles null response (navigation failure) gracefully", async () => {
    const page = makeMockPage({ goto: jest.fn().mockResolvedValue(null) })
    const result = await executeTool("navigate", { url: "https://example.com" }, page) as Record<string, unknown>
    expect(result.statusCode).toBeNull()
  })

  it("returns error object for unknown tool name", async () => {
    const page = makeMockPage()
    const result = await executeTool("unknown_tool", {}, page) as Record<string, unknown>
    expect(result.error).toMatch(/Unknown tool/)
  })

  it("fill_field calls page.fill with selector and value", async () => {
    const page = makeMockPage()
    const result = await executeTool("fill_field", { selector: "input[name=email]", value: "test@example.com" }, page) as Record<string, unknown>
    expect(page.fill).toHaveBeenCalledWith("input[name=email]", "test@example.com", expect.any(Object))
    expect(result.success).toBe(true)
  })

  it("fill_field returns success=false if page.fill throws", async () => {
    const page = makeMockPage({ fill: jest.fn().mockRejectedValue(new Error("not found")) })
    const result = await executeTool("fill_field", { selector: "#nope", value: "x" }, page) as Record<string, unknown>
    expect(result.success).toBe(false)
  })
})
