# AI Vince server

Serves the Omni Method pages and the analysis endpoint behind `ai-vince.html`. The browser never holds an API key: it
posts the console's snapshot and the conversation to `/api/vince`, and this server calls the model.

```
cd server
npm install
ANTHROPIC_API_KEY=sk-ant-... node vince-server.mjs      # http://127.0.0.1:8787
```

Open `http://127.0.0.1:8787/`, enter a business, press **AI Vince** in the toolbar above the results. (The pages must
be served from here, not opened as files: the console hands its figures to AI Vince through the browser's storage for
that address.)

| Setting | Default | |
|---|---|---|
| `PORT`, `HOST` | `8787`, `127.0.0.1` | Bind to `0.0.0.0` only behind your own TLS and access control: the endpoint spends your API credit. |
| `VINCE_MODEL` | `claude-opus-5-5` | The model behind AI Vince for now. |
| `VINCE_EFFORT` | `medium` | `low`, `medium`, `high`, `xhigh` or `max`. |
| `VINCE_FALLBACKS` | on | `off` disables the server-side refusal fallback. |
| `VINCE_MOCK` | off | `1` returns canned replies and calls nothing (demos, tests). |

Limits: 12 requests a minute per address, 6 at once, 200 KB a request, 24 messages a conversation.

## Replacing the model with VTG's AI Vince

Everything model-specific is in `askModel()` in `vince-server.mjs`: it receives the snapshot and the conversation and
calls `onText(delta)` as text arrives. Replace its body with a call to VTG's AI Vince; the page, the snapshot and the
streaming protocol do not change. The persona and the rules for reading the figures are in `SYSTEM` and `ANALYZE` above it.

## What is sent

The snapshot (`omni.vince.v1`: the inputs and every output the console computes, about 12 KB) and the business name if
one was typed. It is sent to the model provider to write each reply. The page says so before the first request.

Tests: `node tests/vince.test.js` (server, with a fake model API) and `node tests/browser.vince.js` (console to page).
