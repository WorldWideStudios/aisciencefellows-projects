import express from 'express';
import path    from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const app  = express();
const PORT = process.env.PORT || 3000;

const GEMINI_API_KEY = process.env.GEMINI_API_KEY || '';
const GEMINI_MODEL   = process.env.GEMINI_MODEL   || 'gemini-2.0-flash';

if (!GEMINI_API_KEY) {
  console.warn('WARNING: GEMINI_API_KEY is not set in your .env file.');
}

app.use(express.json());

// Serve the HTML file
app.use(express.static(path.join(__dirname)));

// Proxy endpoint — called by the browser instead of Gemini directly
app.post('/api/chat', async (req, res) => {
  const { system, messages, maxTokens = 1000 } = req.body;

  const url = `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent?key=${GEMINI_API_KEY}`;

  const contents = messages.map(m => ({
    role: m.role === 'assistant' ? 'model' : 'user',
    parts: [{ text: m.content }]
  }));

  try {
    const geminiRes = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        systemInstruction: { parts: [{ text: system }] },
        contents,
        generationConfig: { maxOutputTokens: maxTokens }
      })
    });

    const data = await geminiRes.json();

    if (!geminiRes.ok) {
      console.error('Gemini error:', data);
      return res.status(geminiRes.status).json({ error: data.error?.message || 'Gemini API error' });
    }

    const text = data.candidates?.[0]?.content?.parts?.[0]?.text;
    if (!text) {
      return res.status(500).json({ error: 'Gemini returned no text', raw: data });
    }

    res.json({ text });
  } catch (err) {
    console.error('Server error:', err);
    res.status(500).json({ error: err.message });
  }
});

app.listen(PORT, () => {
  console.log(`Server running at http://localhost:${PORT}`);
  console.log(`Open: http://localhost:${PORT}/simulation-platform.html`);
});
