# Playwright Service

Express server providing browser-based operability checks for the Agent Operability Report.

## Status

**MVP: mock only.** All checks return score 0. Real Playwright logic added in V1.0.

## API

### POST /scan

Request: `{ "url": "https://example.com" }`

Response:
```json
{
  "status": "complete",
  "score": 0,
  "maxScore": 25,
  "checks": {
    "semanticHtml":       { "score": 0, "maxScore": 7, "found": false },
    "ariaAttributes":     { "score": 0, "maxScore": 5, "found": false },
    "stableUrls":         { "score": 0, "maxScore": 5, "found": false },
    "keyboardNavigation": { "score": 0, "maxScore": 4, "found": false },
    "noCaptcha":          { "score": 0, "maxScore": 4, "found": false }
  }
}
```

### GET /health

Returns `{ "status": "ok" }`.

## Local dev

```bash
npm install
npm run dev
```

## Implementing real checks (V1.0)

Replace `MOCK_RESULT` in `src/index.ts` with Playwright logic:
- `semanticHtml` — count `<main>`, `<nav>`, `<article>` etc.
- `ariaAttributes` — count `role` / `aria-*` attributes
- `stableUrls` — check hash vs real URL navigation
- `keyboardNavigation` — verify focus indicators
- `noCaptcha` — detect CAPTCHA widgets
