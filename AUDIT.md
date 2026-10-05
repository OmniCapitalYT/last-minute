# The Omni Method: audit of the console against the specification

`index.html` is the whole application: one self-contained page, with no external
requests. It is checked against *The Omni Method* specification (24 pages). This
file records what was wrong with how the console turns inputs into reported
metrics, what changed, and what was deliberately left alone.

Run the checks:

```
node tests/model.test.js       # 1,751 model invariants, no browser needed
node tests/browser.sweep.js    # every select and slider at 1440px and 390px (needs Playwright)
```

## Conceptual errors fixed

| # | Defect | Effect on screen | Fix |
|---|--------|------------------|-----|
| 1 | **The realised price could exceed the ask.** Anchoring pulled an underpriced ask only part of the way down. | At the framework example (ask 0.79× model value) the "expected realized price" was 116% of the ask. The panel beside it quoted IBBA's 85–102%. | The ask is a ceiling on the realised price, through a smooth minimum so the optimiser never sits on a kink. The only headroom above 100% is where IBBA's band averages above the ask (102% at $5M+). |
| 2 | **The outcome fan ignored the ceiling as well.** | Bull case of $6.3M on a $3.2M ask. | Quantiles are capped too: `q(p) = min(free quantile, ceiling)`, and `q(.5)` is still the median exactly. The mean of the capped distribution scales the measured 1.0907 ratio by the share of the mean that survives the cap. |
| 3 | **Expected proceeds rose again at extreme asks.** The gap penalty runs out at Pepperdine's last bucket (>50%), but anchoring kept climbing to 2.4×. | Asking 2.5× value "earned" more than asking 1.8×. All 64 industry/size cases in the test failed. | Anchoring and the ceiling both stop rising past `RHO_MAX` = 1.5×, the largest gap the survey resolves (smoothly, so there is no kink in the search range). Past that point, a higher ask only costs closing probability. |
| 4 | **The competition premium was always positive** (`κ·ln(1+n/3)`), even though BIZCOMPS prices are closed sales that already include ordinary competition. | About +4% on every deal. A business marketed exactly like its peers was priced above its own comparables. | Centred on the industry's typical pool: deeper than usual earns a premium, thinner than usual costs a discount, typical costs nothing. |
| 5 | **Mean and median were mixed.** The hero showed `P_C × mean`; the optimiser cards and the "lifts proceeds by" line used `P_C × median`. | The cards disagreed with the hero by 9%. "Do nothing" showed a positive lift. | Expected proceeds is `P_C × E[price]` everywhere, including the U equation. |
| 6 | **Value gap, interventions and sensitivity measured the ask-capped price.** | On an underpriced listing every quality fix read as worthless and repricing as pure upside. | The value gap and ΔValue use model value (what the business supports). ROI and ΔE[proceeds] use expected proceeds, measured on top of a free reprice (which is how the optimiser composes them). Sensitivity shows ∂V and ∂E[proceeds]. |
| 7 | **A general manager's salary never came off earnings.** SDE adds back the owner's pay, not an employee's. | "Hire a GM" ranked as the single best intervention. | The salary is deducted from normalized earnings, and a buyer capitalises that at the multiple. |
| 8 | **Expected loss was computed and never shown.** The spec says the console reports expected loss. | Survival risk showed default probability only. | The survival-risk tile shows expected loss and severity (loss given default, LGD). |
| 9 | **Equation panels typeset formulas the app no longer uses.** | §8 showed the judgment stack above a value from the fitted equation. §5–7 showed the judgment logistic as "reported". §9 showed a proportional-hazards model with covariates. §23 said "lognormal". | Each panel now shows the formula that produces the number beneath it. |
| 10 | **Provenance labels.** "Expected realized price" and "Expected proceeds" were labelled *aggregate*, but anchoring and competition are judgment. | The labels overstated how measured these figures are. | Labelled *judgment*, with a tooltip saying why. |

## Wiring and layout defects fixed

- The input rail was declared `position: sticky` but never stuck. A later
  `.panel{position:relative}` rule overrode it, and `overflow-x:hidden` on
  `html` and `body` turned `body` into a scroll container. Changed to `clip`.
- `font-variant-numeric: tabular-nums` was applied to all prose. In this font it
  also widens the comma and full stop, which produced "18 , 941" and
  "metrics . Every". Tabular figures now apply only to numeric columns.
- State and franchise changes triggered `render()` twice, and every slider
  gesture did too. Renders are now coalesced to one per animation frame.
- The file was wrapped in an artifact-export skeleton (a second
  `<html><body>` with a light theme). That wrapper is removed.
- Long equations were clipped at the panel edge. They now scroll horizontally.
  On phones, wide tables scroll inside their panel instead of running off the
  page.

## Left as documented judgment (not changed)

- **The anchoring strength (α = 0.55) and the 0.45 maximum gap penalty** come
  from the spec. Because of them, a patient seller (θ = 0.75) is told to ask
  about 1.57×, with a 34% chance of closing. That follows from the spec's own reasoning ("~1.4× when the owner
  is content to keep it"), but neither number is estimated.
- **Quality positioning moves the median, and the full residual fan is then
  applied around it.** If quality really explains part of the residual, the
  conditional spread should be narrower. No data measures how much, so this was
  left alone.
- **The SBA rate is fixed at 10.5%** and is not on the rail. The fitted rate
  coefficient (+0.17 per point) makes this matter: at 7.5% the default
  probability would be about 40% lower.
- **Buyer archetypes, intervention costs and the category scores** are
  unchanged judgment, as the spec says.

## Visual layer

A "cosmos" layer (`<style id="cosmos">` and `<script id="cosmos-js">`) sits on
top of the existing sheet and never touches a figure. It adds:

- a full-height masthead with a 3D orrery and a constellation;
- a fixed spiral galaxy, nebula colour and shooting stars;
- a scrolling deep field behind the glass panels (black hole, edge-on galaxy,
  ringed ice world, comet, satellite);
- a mission-trajectory line with a ringed node and a stage number for every
  section;
- a planetary Omni-score dial, and a starfield, banded planet and moon in the
  hero orbit;
- a dawn-on-a-planet horizon at the foot of the page.

Spacing is roughly doubled throughout. All motion stops under
`prefers-reduced-motion`, and the heavy layers drop out below 820px.
