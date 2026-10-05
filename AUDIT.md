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

## Revisions (v3)

Applied from `revisions.pdf`. The v3 layer (`<style id="v3">` and
`<script id="v3-js">`) overrides parts of the cosmos layer described above.

1. **Two scores.** The *business score* prices the same profile at the ask that
   maximises its expected proceeds, so it measures the business alone. The
   *Omni score* uses the ask as entered. The caption says how many points the
   ask costs. Because the business score is taken at the optimum, it can never
   be the lower of the two (the sweep checks this).
2. **Exact inputs.** Every slider has an editable value beside it. It accepts
   `$1.45M`, `1,450,000`, `450k`, `14%`, `none` and similar.
3. **Adaptive ranges.** Earnings run from 2% to 85% of revenue, the ask from
   0.4× to 2.5× of model value, and the budget up to 15% of revenue. A typed
   value outside the range is kept exactly; the slider just rests at the end of
   its travel.
4. **Typefaces.** The monospace face is removed, including its embedded font
   files (54 KB). Bricolage Grotesque, the masthead face, is used for display
   and figures. Schibsted Grotesk is used for text, with a Helvetica fallback.
   Wide letter-spacing and all-caps labels are gone. Equations still use
   KaTeX's math fonts.
5. **3D solar system.** A canvas with true perspective projection. Orbit arcs
   pass behind and in front of the sun, bodies are depth-sorted and lit from
   the sun's direction, the ringed planet's ring crosses its disc, and the
   camera drifts with the pointer.
6. **Preloading.** The console sits behind a loading bar until fonts, planet
   sprites, the first model run, every equation and the data tab are done.
   - Equations whose source has not changed are no longer re-typeset.
   - Off-screen equations are typeset when they scroll near, or in idle time.
   - Renders are coalesced to one per animation frame.
   - Glass blur is removed from the panels.
   - The sky shader runs at 30 fps.
   - A render went from about 60 ms to about 25 ms.
7. **Focal planet.** The hero is now a lit, banded planet with bear, base and
   bull orbits in 3D. The closing-probability trail brightens toward a flared
   probe and sheds sparks, and it eases to each new value.
8. **Plexus.** The stars drift and link to their neighbours, and they reach for
   the cursor.
9. **No AI-design tropes.** Removed:
   - stage numbers and "begin descent / end of transmission";
   - bracket corners, pulse dots, version tags and gradient text;
   - glowing pills, film grain, scroll-reveal fades, the split-word heading
     animation and the fixed gas giant.

## Final audit (independent pass)

An independent review checked every routine against the spec and reproduced each
finding numerically before it was fixed.

**Fixed**

- **The proceeds optimiser repriced to the wrong ratio.**
  - Every reprice used the utility-optimal ratio, which depends on θ (1.57× at
    θ = 75%).
  - As a result, "maximize expected proceeds" told a patient seller to do
    nothing (net $1.73M), when repricing to the proceeds optimum (1.10×) with
    three interventions nets $2.34M.
  - The intervention table and the value-gap note inherited the same error.
  - Each objective now reprices to its own optimum. A test checks that the
    proceeds optimum is independent of θ.
- **Typed amounts were truncated.** The parser read only the leading number:
  "1e6" read as 1 and "12.3.4m" as 12.3. The whole string must now be one
  number with an optional unit; anything else is rejected and marked.
- **Stepped sliders snapped typed values.** Typing 63 buyers gave 65. Typed
  values are now kept exactly until the slider is dragged.
- **The earnings clamp was not stored.** Earnings above 92% of revenue were
  clamped for display but kept in the input store, so raising revenue later
  restored the impossible figure. The clamped value is now stored.
- **Labels that disagreed with their numbers:**
  - The hero legend put the unanchored model value between two realised-price
    quantiles. It now shows the median sale.
  - The ceiling row showed `ask × c` instead of the ceiling actually used,
    which is held at 1.5× model value.
  - The mean row cited ×1.0907 beside a capped mean of 0.88× the median.
- **Nits:** deals of $5M and up were labelled with the SBA's $2–5M band (7(a)
  loans stop at $5M); the buyer-pool sensitivity row never flagged one-sided
  differences; there was an unfloored `log10` in the judgment build.

**Verified correct**

- Value equation coefficients, the hinge, and its slope beyond the cap.
- The calibration lookup and the industry fallback chain.
- The risk logistic, including the state effect and LGD.
- `ncdf` (max error 2e-7) and `nqnt` (Acklam).
- The Fritsch–Carlson spline: monotone and C1.
- The fan quantiles: exact at all 15 knots.
- `softMin` and the capped mean.
- Golden-section search: within 2.5e-9 of brute force over 160 cases.
- The optimiser bitmask, cost and day aggregation, and order-independence.
- Unit handling (thousands, 30.44 days per month, log bases).
- Business score ≥ Omni score in 800 of 800 cases.

**Noted, unchanged**

- The spec says the p10/p90 band implies σ = 0.472. The shipped quantiles give
  0.468, and that is what the page shows.
- The gap penalty has a slope kink exactly at a 0% gap (no penalty below model
  value, by design). No optimum sits on it.

## Second logic audit (economic and statistical soundness)

This pass asked whether the formulas make sense, not just whether they match the
spec. Each finding was reproduced before it was fixed.

**Fixed**

- **The score let size back in through revenue.**
  - The reference population was built at the industry's typical margin. The
    fitted value prices revenue, so a business with a different margin was
    scored against peers of a different size.
  - At fixed revenue, raising earnings from $0.6M to $3M tripled value but
    took the business score from 99 to 6.
  - The reference now shares the subject's earnings and revenue. With
    transferability at its size-adjusted medians, the score is flat across
    earnings.
- **A median business scored 53–54, not 50, on the business score.** The
  subject was priced at its proceeds optimum against peers priced at the market
  ratio. The business score now has its own reference, priced at the optimum.
  It is exactly 50 for a median business in all 80 industry and size
  combinations. Because the two scores now use different peers, an ask near the
  optimum can put the Omni score slightly above the business score; the caption
  says so.
- **Cliffs at the published size-band edges.** $1 of earnings across $5M of
  value added 76 days to close and $73k of expected proceeds; cash at close
  jumped at $2M. Band medians are now values at each band's geometric centre,
  interpolated in ln(price). Months to close, LOI to close, share of the ask
  and cash at close are all continuous.
- **The strategic premium had no bound.** The synergy pool scales with revenue
  but was capitalised at the earnings multiple, which reached +160% of value at
  thin margins. A buyer now pays away at most 40% of value in synergy.
- **The capped mean could exceed the ceiling** for asks under about a
  millionth of value, because a $1 floor was applied after scaling. It is now
  computed in ratio space.
- **Labels:**
  - The time-to-close curve now says it is conditional on closing.
  - The buyer table's close column reads "Closes if engaged".
  - The value gap counts only changes that add value.
  - The score self-check now tests size-invariance instead of a hard-coded
    pass.

**Judgment, unchanged**

- **The quality composite assumes the nine dimensions are independent**
  (sum / √9), as the spec states. Correlated dimensions would make a good
  business look less extreme, but no dataset measures that correlation.
- **The utility's retained-business branch uses θ × model value.** That is a
  value to the owner, not a sale-price distribution.
