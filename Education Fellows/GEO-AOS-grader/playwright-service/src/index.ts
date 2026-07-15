import "dotenv/config"
import express from "express"
import { scanUrl } from "./scanner"
import type { ScanRequest } from "./types"

const app = express()
app.use(express.json())

app.post("/scan", async (req, res) => {
  const { url } = req.body as ScanRequest
  if (!url || typeof url !== "string") {
    res.status(400).json({ error: "url is required" })
    return
  }
  console.log(`[scan] requested for: ${url}`)
  try {
    const result = await scanUrl(url)
    res.json(result)
  } catch (err) {
    console.error("[scan] error:", err)
    res.status(500).json({ error: "scan failed" })
  }
})

app.get("/health", (_req, res) => {
  res.json({ status: "ok" })
})

const port = process.env.PORT ?? 3001
app.listen(port, () => {
  console.log(`Playwright service listening on port ${port}`)
})
