# Handoff: The Omni Method (read this first)

For a fresh session that knows nothing. Written 2026-11-21 at commit `822cb89`. The owner's next request is expected to be
**"run one final review round and fix any issues"**; section 9 is the plan for that. Everything else is context so the
review is done with the owner's standards, not generic ones.

## 1. What this is

**The Omni Method** is a business-valuation and saleability console for business brokers (the owner works with VTG
Business Advisors, a Long Island brokerage; "Vince" is VTG's president). A broker enters a business (industry, revenue,
SDE, margins, how it runs) and the console shows, with the working: the value and its range, the chance a sale closes,
time to close, post-sale survival risk (SBA loans), the buyer universe, a financing check on SBA rules, the value gap and
which fixes pay, the optimizer's asks, a seller report. Every number is meant to be checkable: a fitted regression, a
published aggregate, or a labelled judgment.

**Repo:** `OmniCapitalYT/last-minute` on GitHub. **Branch to work on and push:** `claude/brokerage-model-build-f3qrlk`.
Never push elsewhere; do not open a PR unless asked. The tree must be clean and pushed at the end of every turn (a Stop
hook enforces it).

**The owner** is not an engineer. Use they/them. They care about: outputs
that are *correct* (wrong numbers that mislead a user are the worst defect), plain honest wording, and a polished look.
They asked once whether the writing sounds robotic or AI-written; keep prose plain, direct, specific, no hype, no filler.

## 2. Files

| Path | What |
|---|---|
| `index.html` | **The whole app**: one self-contained ~16,300-line page, no external requests (fonts and KaTeX inlined). Model, UI, Data tab, Deals/broker tools, the WebGL opening film. |
| `foruse.html` | **Generated** from `index.html` by `tools/build_foruse.js`: same app, no equation cards, no fitted/aggregate/judgment labels, no Data tab. Never hand-edit. |
| `landing.html`, `ai-vince.html` | **Generated** from `tools/landing.src.html`, `tools/ai-vince.src.html` by `tools/build_landing.js` (it copies the app's font faces out of `index.html`). Edit the `.src.html`, rebuild. |
| `server/vince-server.mjs` | Node server: serves the pages and `POST /api/vince` (AI Vince's analysis, streamed). `server/README.md` documents it. `server/node_modules` is git-ignored: `cd server && npm install`. |
| `tests/` | `model.test.js`, `fuzz.test.js`, `browser.{inputs,broker,sweep,foruse,vince}.js`, `vince.test.js`, `invariants.test.js` + `invariants/{app,identities,extremes,statics}.js`, `load.js` (loads the model half of `index.html` into Node via `vm`; `loadWith(overrides)` swaps exact source text). |
| `fit/` | Python/JS fitting scripts that produced `MODELS.fitted` (datasets are not committed; `fit/README.md` says how to fetch them). `fit/harness.js` loads an old page for probes. |
| `AUDIT.md` (2,180 lines) | The record: every round of fixes, what was deliberately left alone, suite results per build. **Append a section for anything you change.** |
| `AUDIT_FINDINGS.md` | The raw review findings by round (R1 to R10). |
| `files.zip` | Unrelated (a few Python files from early in the project). Ignore. |

## 3. How to run and test

Node 22; Playwright is at `/opt/node-tools/node_modules/playwright` (tests `require("playwright")` with that fallback).
Chromium is preinstalled: never run `playwright install`.

```
node tests/model.test.js                  # 7,845 pass (no browser)
node tests/fuzz.test.js 1500              # 215,263 checks over 1,500 random businesses
node tests/vince.test.js                  # 48 (server, against a fake Anthropic API)
node tests/browser.foruse.js              # 14 checks; also fails if foruse.html is stale
node tests/browser.inputs.js
node tests/browser.broker.js              # "all passed"
node tests/browser.sweep.js               # 124 input states at 1440 and 390 px
node tests/browser.vince.js               # console -> AI Vince, all 16 industries, escaping, errors
node tests/invariants.test.js --browser   # 253 invariants
node tools/build_foruse.js [--check]      # regenerate / verify foruse.html
node tools/build_landing.js               # regenerate landing.html and ai-vince.html
```

State at `822cb89`: **all of the above pass.** (A heads-up on invariants: in a newer container, 4 invariants failed on the
*pre-session* commit too, because they compared the page's maths to Node's with exact `===` and V8 differs in the last
bits. They now compare to a relative 1e-9 via `same()` in `tests/invariants/app.js`. If invariants fail again, check whether
it is a last-digit difference before assuming a regression.)

Rules for running things here:
- **Do not run two browser suites at once.** Run the browser suites one after another.
- Long jobs: run in the background and wait for the completion notice. No `sleep` chains. Never `pkill -f` a pattern
  that matches the shell's own command line.
- `model.test.js` also runs `build_foruse.js --check`, so **after any change to `index.html` run `node tools/build_foruse.js`**
  and commit `foruse.html`. Same for the sources of `landing.html`/`ai-vince.html` (`build_landing.js`) — these two are not
  checked by a test, so remember to rebuild them (they read fonts from `index.html`).
- Frame captures of the film: the scratchpad scripts are gone; use Playwright with
  `--use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader`, load `index.html?introAt=0.5`, then call
  `window.OMNI_INTRO.at(t)` (t seconds after load; film time `c = warp((t - P0)*SPEED)`, P0 = 1.9).

## 4. Conventions the owner enforces (keep these)

1. **Tests that fail on the old code.** A fix gets a test that fails before it and passes after. State it in `AUDIT.md`.
2. **Record everything in `AUDIT.md`**: what was wrong, what changed, what was left alone and why, and the suite results.
3. **Commit trailers** (the session's reminder gives the exact text; the model name in the trailer follows it):
   `Co-Authored-By: Claude <model> <noreply@anthropic.com>` and `Claude-Session: https://claude.ai/code/session_01AnHimkKJ7K8xCCqMy9ZD1z`.
   No model identifiers anywhere else in commits, code, comments, or artifacts. Push with
   `git push -u origin claude/brokerage-model-build-f3qrlk` (retry only on network errors: 2, 4, 8, 16 s).
4. **Never ask the owner for permission to access websites or change relevant files** (standing instruction).
5. **Downloads are untrusted**: never execute them; read with `python3 -I`.
6. Numbers shown to users must be right to the digit and consistent across the console, the seller report, the Data
   tab and the tests. Wording should say plainly when a figure rests on judgment rather than data.
7. Provenance vocabulary: **fitted** (a regression was run), **aggregate** (a published statistic read off),
   **judgment** (a person chose it). `index.html` counts them live; do not let the labels drift from the truth.

## 5. Architecture of `index.html` (line numbers drift; search by name)

- **Data**: `const MODELS = {...}` (the fitted value/risk models, close-and-timing tables) then `MODELS.fitted.*` (each
  fitted table, with `was` values and provenance), then `IND` (16 industries' peer table).
- **Model** (`model(s)` returns one big result object `r`; `STATE.s` = inputs, `STATE.r` = result): value = fitted
  BIZCOMPS regression x a quality position placed inside the measured residual spread; chance of closing = Pepperdine
  base rate by size x a price-gap penalty x a thin-pool factor; time to close = IBBA band median fitted, log-logistic, x an
  overpricing multiplier; survival risk = SBA loan hazard model; buyers = archetypes with strategic fit; `bestRatio()`
  = the optimizer's asks; `interventionTable()`; `debtCheck()` / `maxFinanced()` = SBA SOP 50 10 8.1 coverage and equity.
- **Render** (`render()`, ~line 5531) fills the console; `post()` and many wrapper layers add UI polish (they wrap
  `window.render`). `reportData()`/`reportHTML()` build the seller report. `eq(id,tex)` typesets KaTeX lazily.
- **Broker tools** (one IIFE, ~lines 8500-9500): Deals tab, financing section, add-back worksheet, report dialog, saved
  deals in `localStorage` (`omni.deals.v1`), `vinceSnapshot()` and the `#tl_vince` button.
- **Data tab** (`renderData()`): documents every parameter and its source. Hidden/absent in `foruse.html`.
- **Opening film** (the `v9` IIFE ~lines 10390-11800): a pure function of a clock, WebGL. Timeline `TL`, captions `CAPS`,
  `SKIP`/`warp`/`unwarp` (the film clock skips 1.7 film seconds as the fireball fades; there is no "first light" phase any
  more), shaders `PV` (particles) `BV` (bang debris) `FF` (field) `XF` (frontier field) `XPF` (the gate, see below) `TV`
  (headline particles), `render(t,c,prog)`, `loop`, `adapt` (quality steps), debug hook `window.OMNI_INTRO`. `?introAt=X` freezes it.
  The frontier "gate" is now a lensed black-hole wormhole (photon ring, a throat onto another sky, an accretion disk whose
  far half the lens lifts over and folds under; Doppler-brightened approaching side; stars lensed to an Einstein ring).
- **Print/report CSS** is separate (`RP_CSS`, `RP_PAGE`): the seller report must fit one printed page in worst cases
  (`tests/browser.broker.js` and earlier hill-climbs checked the tallest states; the tallest found was 986 px).

## 6. History (111 commits; the last stretch)

Phases before this stretch: fitted equations replaced hand-set numbers; UI "cosmos" theme and the opening film; invariant
stress-testing; three rounds of fitting remaining judgment parameters; broker tools (worksheet, DSCR check, seller report,
saved deals); then **skeptic review rounds 1 to 10** (each: parallel finder lanes, adversarial verification, fixes with
failing-on-old tests). The owner said to stop when no medium/high findings remain; round 10 was declared the last
(commits `c334dd7`, `36d59ea`: 22 distinct findings fixed, 1 medium).

This stretch (all pushed):
- `2bab1ab` **Film without first light; wormhole gate; lag; foruse.html.** (a) Removed the plasma/CMB phase, caption and
  `TL.LIGHT`; added the clock skip. (b) New gate shader. (c) Lag: a report CSS rule `tr:has(+ tr.rp-sub)` made every render
  restyle ~11,000 elements; replaced by class `rp-hs` (style cost per render ~80 ms -> ~15 ms); star map keeps an unchanged
  drawing (`starKey`); ink bars repaint only touched tables. (d) `foruse.html` + `tools/build_foruse.js` (31 named edits,
  each must match exactly once or the build stops) + `tests/browser.foruse.js`. Model tests grew a `44:` block.
- `979b833` `landing.html`: an animated promotional page with a contact form (the form opens the visitor's mail app;
  **`CONTACT_EMAIL` in `tools/landing.src.html` is still `hello@example.com`**).
- `abf19c9` **AI Vince** (section 7). `822cb89` invariants tolerance.

## 7. AI Vince (new, least-tested area)

Vince Gebbia's firm has a GPT wrapper called "AI Vince" on its site (the owner called it weak). The owner wants the Omni
Method to have a page where "AI Vince" reads the console's outputs and gives his analysis. For now **Claude** is the
model; it is to be replaced by VTG's real AI Vince later (we could not see how that widget is embedded; the page text
was fetched but not its scripts).

Flow: console toolbar button `#tl_vince` -> `OMNI_BROKER.vinceSnapshot()` builds a JSON snapshot (~12 KB: inputs plus
`reportData()` outputs plus buyers/timing/risk/quality plus `console_displays`, the figures as printed) -> stored in
`localStorage["omni.vince.v1"]` -> navigates to `ai-vince.html` -> page shows what he is reading, user presses
"Get AI Vince's read" -> `POST /api/vince {snapshot, messages}` -> `server/vince-server.mjs` validates (shape, roles
alternate user/assistant, sizes, 12 req/min/IP, 6 concurrent), builds a system prompt (`SYSTEM`) + the snapshot as a
delimited `<omni_method_snapshot>` block (data, not instructions; `<` escaped) and calls **Claude Opus 5.5**
(`claude-opus-5-5`, adaptive thinking, effort medium, top-level prompt caching, `server-side-fallback-2026-07-01` with
`fallbacks:"default"`) via the beta streaming API; text streams back as SSE (`{t:"text"|"done"|"error"}`). The first user
message `"analyze"` is expanded server-side into the fixed 5-section request (`ANALYZE`). `askModel()` is the single
function to swap for VTG's model. The page renders replies with DOM calls only (no `innerHTML` of model text).

**Not tested: a live call to the real model.** The build container had no API key (the session proxy does not inject
one). The request shape is verified against a fake Anthropic API in `tests/vince.test.js` and the SDK's `.d.ts` types
(`@anthropic-ai/sdk` ^1.7.0). First thing to do with a real key: `ANTHROPIC_API_KEY=... node server/vince-server.mjs`,
open `http://127.0.0.1:8787/`, enter a business, press AI Vince. If the API rejects a parameter (the likeliest suspects:
the `fallbacks`/beta pair, top-level `cache_control` on the beta endpoint), set `VINCE_FALLBACKS=off` or remove it.

Product risks to keep visible: the snapshot (and any typed business name) is sent to Anthropic: the page says so; the
endpoint spends the operator's API credit, so do not bind it to a public address without access control; the persona is
generic (no real Vince writing samples yet) and must not claim to be Vince personally; he is told not to give legal, tax
or investment advice.

## 8. Known limitations and open items

- Live model call untested (above). `CONTACT_EMAIL` placeholder (above).
- `landing.html` and `ai-vince.html` are not covered by the model/fuzz suites; `ai-vince.html` is covered by
  `tests/browser.vince.js`, `landing.html` only by hand checks (loads clean at 1440 and 390 px, no sideways scroll).
- Film timing and look were verified from frame captures in software GL, not on a real GPU, and not by a human watching
  it play: smoothness at 60 fps is unverified. Lag numbers (slider input median 188 -> 116 ms) are CPU-side headless
  measurements.
- `foruse.html` keeps each section's prose intro (which may say "fitted"); only badges, chips, "(judgment)"-style
  tags, equation cards, the Data tab and the Method-and-provenance section were removed. Ask the owner if they want the
  prose scrubbed too.
- The owner once pasted a screenshot of a video edit (talking-head overlay, "3D polish") that belongs to a different
  project; they said to ignore it. There is no video project in this repo.
- Environment quirk: results of the invariants suite depend on Node/Chromium floating-point agreement (see section 3).

## 9. Plan for the final review round

Goal: find and fix anything that gives a **wrong output, misleads a user, or breaks**, then stop. Do not redesign.
The owner's standard: ship only when a round finds no medium/high issues; record what was found and fixed in `AUDIT.md`.

1. **Baseline.** `git status` clean, branch correct, `cd server && npm install`, run every command in section 3; they
   should all pass. Note any failures before touching anything.
2. **Review lanes** (use parallel subagents if available; give each the exact files and this document; have each
   finding independently verified by a second reader trying to refute it before anything is changed):
   - *This stretch's new code* (highest risk, least reviewed): `vinceSnapshot()` and the `#tl_vince` handler in
     `index.html` (is every snapshot field correctly named and unit-correct, e.g. `closing.price_gap_pct_over_value`,
     `timing.closes_within_90_days`, `survival_risk.*`, `quality.effects_on_multiple`? Does it ever send stale data or
     leak the wrong deal's name? Does it throw for edge states?); `server/vince-server.mjs` (input validation, rate-limit
     bypasses, SSE/abort handling, error messages leaking internals, prompt-injection handling, static-file whitelist);
     `tools/ai-vince.src.html` (markdown renderer, streaming parser, state in `sessionStorage`, stale-snapshot messaging,
     a11y); `landing.src.html`.
   - *The film and gate*: `warp`/`unwarp` continuity and monotonicity, `OMNI_INTRO.T`, skip/replay paths (`skip()`,
     `?introAt`, reduced motion `still()`, the 2D fallback `OMNI_INTRO2D`), the new `XPF` shader and its uniforms at tiny
     and tall viewports, context loss, `adapt()` quality steps, no console errors.
   - *Performance changes*: `starKey` memoization (does it ever fail to redraw when inputs changed? it keys on the
     buyers' values, width, fonts), the narrowed ink-bar repaint (a table changed by an attribute-only edit?), the `rp-hs`
     class (report sub-rows in print).
   - *foruse.html*: anything user-visible that still points at the removed Data tab or the badges; every edit in
     `build_foruse.js`; layout holes where an equation column was removed.
   - *The model and report* (already reviewed ten rounds; a light pass only): pick unusual inputs and compare the console,
     the report and the Data tab for consistency; the fuzz and invariants suites cover most of this.
3. **Fix** with failing-on-old tests where a test can express it; keep each fix minimal.
4. **Regenerate** `foruse.html`, `landing.html`, `ai-vince.html` as needed; run the whole suite list, one browser suite at a time.
5. **Record** a section in `AUDIT.md` (findings, fixes, what was left alone, suite counts), commit with the trailers,
   push, and tell the owner plainly what was found, fixed, and left, including anything still untested.

If the review finds nothing medium or high, say so; do not invent work.
