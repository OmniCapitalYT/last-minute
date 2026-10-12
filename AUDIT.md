# The Omni Method: audit of the console against the specification

`index.html` is the whole application: one self-contained page, with no external
requests. It is checked against *The Omni Method* specification (24 pages). This
file records what was wrong with how the console turns inputs into reported
metrics, what changed, and what was deliberately left alone.

Run the checks:

```
node tests/model.test.js       # model checks and pinned figures, no browser needed (7,458 at commit 79a18c0)
node tests/fuzz.test.js 1500   # property invariants on 1,500 seeded random businesses
node tests/browser.inputs.js   # typed inputs, validation, tabs and the Data tab in a real browser (needs Playwright)
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
  from the spec. Because of them, a patient seller (θ = 0.75) was told to ask
  about 1.57×, with a 34% chance of closing (superseded: see "Realised-price fan" below; now a near-tie, shown as a range). That follows from the spec's own reasoning ("~1.4× when the owner
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

## Third logic audit (regressions, captions, data tab)

**Fixed**

- **The value gap counted a change that loses value once bundled.** Hiring a
  GM adds value alone but costs $318k inside the full bundle: the quality
  percentile saturates while the salary deduction keeps growing. The gap now
  drops any change whose removal raises the bundle's value: +$527k became
  +$845k at the defaults.
- **Reset left the state and franchise inputs set.**
- **The realised price could reach 107.8% of the ask** for e-commerce. The
  ceiling now uses IBBA's band level (at most 102%) rather than the BizBuySell
  industry factor, which describes typical realisation, not a cap. A test
  covers all 16 industries.
- **A wrong sensitivity note.** At a gap of 100% or more, the closing
  probability is pinned at its floor, and the note had claimed the ask sat
  under model value. That case now has its own message.
- **The realisation row labelled an interpolated figure with a band name.** It
  now names the IBBA size curve.
- **Calibration self-checks tested other things than they printed:**
  - the $20M anchor check passed below 7.2× under a "6.0–6.5×" label;
  - the advisor-engaged close rate was checked on the broker channel;
  - the upper close-rate bound was looser than its label;
  - the score check could never fail.

  Each now tests exactly what it prints, so two rows honestly read "off": the
  fitted multiple of 2.35× at the BizBuySell median profile (against 2.0×), and a
  judgment-stack anchor of 6.77×, which the reported value does not
  use. (A third, the BizBuySell days-on-market row, has read off since the October 2026
  median refit; see the last section.)
- **The Data tab showed stale figures:**
  - pooled close rates instead of the recent ones the model uses;
  - σ 0.485 "lognormal" and an 80% interval of 0.52–1.82×;
  - a "stepped" penalty;
  - an old quality band;
  - a 73.9% loss-given-default figure;
  - "Omni score weights".

  All are now read from the live model.
- **Nits:**
  - `capLo` and `capHi` are renamed `ceilAt` and `floorAt` to match what they
    do.
  - The list note no longer implies that delay cost moves the ask.
  - Money boxes reject percentages and negative amounts instead of silently
    clamping them.

**Unchanged:** the GM's cost scales with revenue (at least $85k, the spec's
figure) in line with "cost scales with company size".

## Fourth logic audit (everything at once)

Earlier rounds each found new problems because each was one reviewer reading the
whole console and fixing what they noticed. This round split the console into five
areas (price distribution, close/timing/risk, scores and buyers, decisions, inputs
and presentation), audited each independently, wrote every finding into one ledger,
and fixed the ledger in a single pass. A property-based fuzz test
(`tests/fuzz.test.js`: 1,500 random businesses across the whole reachable input
space, about 79,000 checks) now guards invariants that must hold for any input,
so a whole class of bug fails at once instead of one case at a time.

**Structural**
- **The realised-price distribution was built backwards.** It drew the measured
  spread around the already-anchored price and then cut it at the ask, so every
  bull case sat exactly at the ask and the expected price if the deal closed was
  0.83 of the ask (IBBA measures 0.85 to 1.02). Each slice of the measured spread
  is now a scenario for what the market will pay. The ask anchors the price
  against that scenario and caps it. A fairly priced listing now closes at about
  0.89 of its ask in expectation, inside the IBBA range, and the bear case no
  longer moves with the ask.

  A first version also weighted each scenario by its own chance of closing. That
  only multiplies correctly with a closing probability built from the same weights,
  and building one smoothed the calibrated gap curve across the whole value spread.
  The proceeds-optimal ask jumped from 1.10× to 1.36× of value. The verifier caught
  the inconsistency, so the calibrated closing probability is kept and price is
  treated as independent of whether the deal closes. That makes
  P_C × E[price] consistent by construction.
- **Better quality could lower expected proceeds.** The typical buyer pool was
  scaled by the subject's own engagement, so on a thin pool a better business got
  a bigger competition discount. It is now measured at a median business's
  engagement (this was caught by the fuzz test).
- **Better quality could add days to close.** It could also move the cash share
  and the base close rate. All three were keyed on the quality-adjusted value, so
  an improvement pushed the deal into a slower size band. They now read the fitted
  value before quality positioning.

**Close, timing and risk**
- The gap penalty froze above a 100% gap, so asks from 2× to $100B had the same
  closing probability and score. It now has a smooth tail that matches the slope
  at 100%.
- The base close rate was described as "conditioned on deal size" but was
  hard-wired to the broker channel. It now runs from broker ($1M) to
  intermediated ($5M) in log size.
- The risk multiple divided a probability at a 10.5% rate by a base computed at a
  different rate mix. Both are now at the same rate.
- `softMin(x, x)` returned 0.983x, so a ceiling equal to the price shaved 1.7%.
  The smoothing width is tightened.

**Scores and buyers**
- The "pays most" buyer could be one that does not look at deals of this size. It
  is now chosen only among buyers that do. Out-of-size rows are greyed, and the
  "pursue first" tag compares the buyer itself rather than its EV.
- The three "typical buyer pool" references (z-score, judgment delta,
  competition) now share one centre.
- The reference-population draws use midpoints, which removed a bias of up to
  1.2 points.
- The hero caption decides "close to optimal" from the share of expected proceeds
  the ask gives up, since both scores sit at 99 for a strong business. It now
  compares against the optimal ask rather than the model value.
- The score bands are rephrased: the top band is the actual top decile, and the
  low bands describe price rather than "risk of a failed process", because the
  closing probability does not depend on quality.

**Decisions**
- The walk-away ask ran past the last gap the closing data resolve, into a corner
  solution. Both recommended asks are now searched only up to 1.5× value. An ask
  at that edge is labelled "test the market", and the note says when the two
  strategies are close.
- The value gap started only from changes that add value alone, which missed
  changes that only pay inside a bundle, and it kept zero-value changes that padded
  cost and time. It now starts from every change and prunes strictly.
- The two optimiser cards said they "select the same programme" when they
  repriced to different ratios. The reprice row now shows the ratio it uses.
- The sensitivity steps were fixed amounts (3 to 10 points), so the ranking
  reflected the step size. Every lever now moves by one peer standard deviation.
- The ΔP_C column in the intervention table was identically zero by construction
  (every row is repriced), so it is removed and the table says why.
- Applying interventions could push earnings above revenue. They are now clamped.

**Presentation**
- The hero shows the expected price if the deal closes, with the likely range and
  the median.
- The multiple table separates the fitted multiple from the quality position. It
  also shows where the judgment stack's bounds bind and what share of closings land
  at the ceiling.
- Equations now match the code: anchoring and the posterior, the buyer value with
  size fit and the synergy cap, competition in dollars (or "no effect: the ask
  binds"), z-score clamping, and one-sd sensitivity.
- The Data tab paragraph claiming the quality sliders "do not move at all" was
  stale and is rewritten. The years-of-history slider is described as feeding only
  confidence and the category bars.
- Grammar and sign nits are fixed: "1 engaged buyer", percentile ordinals held to
  1st to 99th, a real minus sign on negative ROI, "no sector match" in place of
  ×1.000, and star-map legend sizes that match the marks.

**Found by the inputs audit and the independent verifier, fixed in the same batch**
- Money boxes applied every keystroke. Typing "8M" for revenue committed $8 first,
  which clamped and stored earnings at $9,200, and rejected entries like "14%"
  left their prefix applied. Money now commits on Enter or leaving the box.
  A rejected or abandoned entry restores the value from before the edit and stays
  outlined, and Escape reverts.
- Earnings above 92% of revenue are clamped and stored where they are typed. A
  revenue drag no longer destroys them.
- "1,5m" is rejected rather than read as $15M. Typed decimals are shown as typed,
  and the delay box uses a fixed locale.
- `money()` printed "$1000k" and had no billions unit.
- Clicking Data then Console quickly landed on Data, so the newest click now wins.
  Reset ran 380 ms late and overwrote changes made in between; it now runs at once.
- With reduced motion, the focal planet kept a stale closing probability after
  scrolling back into view. The survival-risk tooltip also kept a stale size band.
- State labels printed the raw population deviation, about 8× the model's effect.
  They now show the change in this deal's default risk.
- The hero "likely" range collapsed to one point (with the mean outside it) when
  most closings land at the ask. It now shows the 80% range and the share at the
  ask. Scenario cards say "the ask ceiling" instead of printing "$X–$X".
- Data tab:
  - the judgment count now matches its table (13 deltas, plus the 9 category
    weights);
  - the fitted count includes the 274 NAICS-6 and 48 state effects, and the risk
    table shows the state coefficient;
  - "9.55%" is replaced by the dataset's own all-loan rate;
  - the quality swing is read from the band.
- Calibration rows print the tolerances they test, and say which multiple they
  test.
- The reset defaults are the framework's worked example ($6M, $1.45M, $3.24M ask).
- `tests/browser.inputs.js` drives all of the above with real keystrokes.

## Fitting the judgment parameters from public data (October 2026)

**Verification pass first.** An independent reviewer reran every test. It also compared
every number on screen with the model in 16 states at desktop and phone widths, and all of
them matched. It found four defects, all fixed:
- The utility equation printed the delay cost rounded to thousands.
- The realisation block claimed the model lands above IBBA's sale-to-ask ratio. Above about
  $1M it does not, so the caption now says so and gives the reason.
- A thin buyer pool did not lower the closing probability. A pool thinner than typical now
  scales P_C by the chance of engaging anyone at all, relative to a typical pool. As a
  result, the optimiser no longer drops outreach where it matters most.
- Red error outlines stayed on after Reset or a slider drag.

**What was fitted.** Most hosts that publish the source data are blocked from this
environment, so each dataset came from a public mirror on GitHub or from the reports
already in the bundle. The scripts are in `fit/`, and `fit/README.md` gives each fetch
command.

| Was hand-set | Now | Data |
|---|---|---|
| SBA rate 10.5% | prime 7.00% (Fed H.15, since 2026-09-17) + 1.42 to 2.50 pts by loan size, measured over the prime on the first business day of the approval month (13 CFR 120.214(c)); first fit was prime 6.75% + 1.5 to 2.0 pts on FY2023 loans | 9,218 variable-rate change-of-ownership 7(a) loans approved FY2025–26, incl. cancelled and undisbursed (SBA FOIA as of 2026-06-30; `fit/sba_risk_refresh.py`) |
| survival risk: logistic on resolved loans only, no horizon | competing-risk hazard: charged off within 10 years if 2023–26 conditions hold (5.6% for the average FY2024–26 loan), 5 years beside it (1.9%); loan-level effects shrunk ×0.74 out of time; years 9–10 borrowed from mature 7(a) loans (×1.20, judgment); staffing dropped (SBA's jobs count is not the console's head count) | 41,200 SBA 7(a) acquisition loans FY2018–26, open loans censored (`fit/sba_risk_refresh.py`) |
| employees = revenue ÷ $150k | receipts per employee by industry and firm size | Census SUSB 2022 |
| GM salary = 2.4% of revenue | BLS industry wage distribution (wages only) read at the firm's size rank, p10–p90, June 2026 $ | OEWS May 2025 (EB-shrunk to parent NAICS) × ECI management W&S to 2026Q2; Census employment by size |
| industry SDE margins 7–21% × size curve, sd 0.45 | fitted 20–30% at $200k SDE (shrunk toward the pooled level), slope 0.075, sd 0.59 | 5,055 broker listings (DealLedger, CC0) |
| equal weight on owner dependence, management depth | 1.24 and 0.60 of an equal share, shrunk toward 1 (neither clearly different from 1) | 5,714 listings with descriptions |
| buyer-type size windows | individual / strategic / financial share by deal value, interpolated between IBBA bands | IBBA buyer mix, 47 complete band-quarters |
| time-to-close curve: Weibull, judgment shape k = 1.42 | log-logistic pinned to the band median, shape β 2.20 under $500K and 2.64 from $500K up (interpolated in ln value); the band medians themselves fitted to the same histograms since (6.54 / 7.75 / 8.02 / 9.03 / 10.14 months, `fit/time_to_close_medians.py`) | IBBA Market Pulse per-band histograms of months to close, 15 quarters, 4,533 closed deals (`fit/time_to_close_shape.py`) |

**What the data could not fit, and why.** The Data tab has a new ledger listing each of these
with the data that would fit it:
- **Listing text and the other quality weights:** listing text priced owner dependence and
  management depth. Recurring revenue, growth and clean books showed no measurable asking
  premium. That neither confirms nor rules them out, so they keep equal weights.
- **Time-to-close:** the 103-day listing panel saw only 164 sales, too few to fit the
  curve's shape. *Superseded:* the shape is now fitted from IBBA's per-band histograms (see the
  table above); only the effect of quality and of the ask on time remain unfitted (the ask's effect is now a
  labelled judgment, T_ELAST 0.10: see "Overpricing costs time" below).
  ~~Open follow-up: refit the time-to-close band medians to the 2020–25 histograms.~~ *Done (October 2026):*
  `fit/time_to_close_medians.py`; see "Logic audits (rounds 0 to 5) and the time-to-close median refit, October 2026" at the end of this file.
  The size-order exception shrinks from 1.4 to 0.7 pts and now starts past about 18 months.
- **Anchoring:** fitting the sale price against the ask needs deal-level pairs of asking and
  sale prices. The model's expected price sits 8 to 14 points below IBBA's average above $1M,
  and no anchoring setting closes that gap: the measured value spread is too wide.
  BIZCOMPS records both prices, so its raw rows would fix this.
- **Records nobody publishes:** the competition premium, intervention effects and category
  weights need the brokerage's own records.
- **Survival risk beyond the data:** no acquisition loan is older than 8.5 years (SBA flags change of
  ownership only since Dec 2017), so years 9–10 of the 10-year figure are a labelled transfer from mature
  7(a) loans. Whether 2023–26 conditions hold is not identified (charge-offs in 2025–26 ran 0.65× the
  2023–24 rate; either period as current puts the 8-year level at 4.1–5.7%, against 4.7% shipped), and the
  FOIA file has no default dates, lender underwriting or business-quality fields. The SEs are parameter-only.

**A second reviewer checked the fits against the raw data.** Every table recomputed from
its source. It found the following problems, all fixed:
- **Owner-dependence weight.** The weight depended on a pooling choice no script made.
  `fit/quality_weights.py` now does the conversion and uses only the owner-operated
  phrase, because "absentee" disagrees with it. It shrinks both weights toward 1 and
  reports the unshrunk figures.
- **Thin-pool factor.** It used this business's own engagement, which made the closing
  probability depend on quality. It now depends on pool size alone, and a test checks
  that quality has no effect at a fair ask.
- **Buyer-mix claim.** The Data tab overstated the buyer-mix data. The fit now
  interpolates the observed bands, which a straight line in log value missed at the top.
- **Wage growth** did not compound to its stated rates.
- **Plausible risks, also addressed:**
  - Industry margins are shrunk by n/(n+50).
  - Staffing ratios use 4-digit industry groups rather than single niches.
  - GM pay grows with firm size by rank.
  - MBOs keep their own window.
  - The prime-rate date is shown.
- **Stale text** about equal weighting and Z/3 is updated.

## UI clean-up (October 2026)

Nothing in the palette or the space layers changed. A final style layer (`v7-clean`) and a
few markup moves tidy the layout:
- **Section headings** sit on one line with the framework tag beside them. The title had
  been squeezed to half its width because the word-split reveal reused the `.split`
  two-column layout class.
- **The hero's eight headline figures** form one even strip under the planet and the
  scores. That replaces two ragged columns that left a large gap under the planet.
  "Price if it closes" and "Chance of closing" are shortened so their labels fit.
- **Tables** lose the bars behind every numeric cell, which had produced five competing
  bar charts per table. Both buyer tags sit with the buyer's name, and number columns are
  spaced from the text column beside them. On a phone, wide tables scroll inside their
  panel instead of crushing their columns.
- **Long equations** are split across lines. Any that are still too wide shrink to fit
  (to 60% at most) and only then scroll, with a fade at the edge.
- **Charts:** the star map gets room for its labels, with its legend under the plot, and
  the time-curve caption no longer sits on the median marker.
- **Stat groups and lists:** the optimizer cards' small stats lose the gap between label
  and value, provenance badges sit on the text line, and lede paragraphs are narrower and
  calmer.

## Realised-price fan (FAN_S), October 2026

`fit/anchoring_realization.py` (revision 4). The earlier note that "no anchoring setting closes the gap" with IBBA was a
fan-width problem, not an anchoring one: sale-to-ask data fix (1 - alpha) * s, and with the value model's whole
spread (s = 1) no alpha brings E[P|close]/ask up to the market averages.

- **fanNodes() fixed (revision 4).** The 48 fan nodes were read off a 4,000-point grid in slices of k = M/N = 83.33
  points: each slice summed 84 points, overlapped the next and divided by 83.33, so every node ran
  0.8-0.9% high (the top one 4.9%) and their mean was 1.1044 against the fan's 1.0924
  (measured mean/median 1.0907). They are now exact slice means (closed form per piece of the piecewise-linear log fan;
  2e-05 from brute force). With the whole spread this lowers E[P|close] by up to -0.15% and, at the typical premium,
  E[P|close]/first ask from 0.870 to 0.868. Every 'current' figure below is the fixed page with the whole spread.
- **What the data show (robust).** At the typical first-ask premium (1.071x value) the whole spread gives E[P|close]/ask
  0.868, short of every like-for-like market average: BizBuySell's deal-level 0.905 on the first ask, and IBBA's
  under-$1M deals (binned by sale price) 0.870 against the model's 0.848. Narrowing the realised-price fan and
  selection on closing (whole fan, each scenario weighted by its own chance of closing; 0.911) both close the gap.
- **What changed.** The realised-price fan keeps FAN_S = 0.80 of the value model's log spread (fan nodes are slice means of
  R(p)^FAN_S; the median, P_C and everything else are unchanged). E[P|close]/ask at the typical premium goes from 0.868 to
  0.890 of the first ask (0.879 to 0.901 of the ask at sale). FAN_S is **calibrated, not fitted**: the
  mechanism is not identified, and it is labelled that way in the Data tab.
- **How sure.** Per source s (premium reading G, Main-Street d): BizBuySell 0.66, IBBA under $500K 0.93, $500K-1M
  0.54 (under $1M as one source 0.85), DealStats 0.89. Averaged over four source structures (IBBA's bands as two
  sources or one; DealStats in or out), three readings of the typical premium and two of the ask: 0.812 (sd 0.20,
  90% 0.50-1.15), rounded to 0.80, which is 0.013 from the rounding cut: 0.75-0.85 are equally
  defensible. P(s < 1) is 0.78-0.89 by structure, but only under narrowing: under selection the sources need
  s of BizBuySell 1.10, IBBA under $500K at least 1.60, $500K-1M 0.91 (under $1M as one 1.47). If the spread of asks across listings were pricing noise rather than information, s would be 0.64, 0.49 and 0.33 at noise sd 0.2, 0.3 and 0.4
  (Empire Flippers' pass-through 0.98 implies a noise sd near 0.04; an analog). Calibrated to 2022+ alone: 0.68.
- **Which ask.** The model's ask is the first listing price. The market sources report the ask standing at sale, about
  1.3% below the first on Main Street (DealLedger net asking-price drift x IBBA months listed to LOI). That figure rests on
  an error rule: 49% of the observed ask changes move by more than 0.5 in logs (median factor 4.4; many with a
  changed title, index-page keys or a factor of ten) and are treated as no change; taken at face value the drift is
  +0.074 a year (the sign flips), excluding them gives -0.030. Empire Flippers' 8.8% gap comes
  mostly from re-pricing as monthly profit arrives and does not transfer.
- **Downside.** The bear scenario narrows: at the typical premium its low end q(.08) goes from 0.52 to 0.60
  of the ask (Empire Flippers' analog q08 of sale/last ask: 0.63); for the framework example the bear band goes
  from $2.29M-$3.05M to $2.64M-$3.16M.
  The Data tab now separates value uncertainty (the whole spread) from the realised-price fan; the scenario equations show R^s.
- **Calibrated near 1.07x, extrapolated above.** FAN_S is set at the typical premium. At asks of 1.4-1.5x value, where the
  patient seller's recommendation is decided, it is an extrapolation, and the two mechanisms part by 4.3-4.7 points of
  E[P|close]/ask. The extrapolation, not the fit, sets the patient-seller answer.
- **Optimiser (decided: shown as a range).** For a patient seller (theta = .75, the default) bestRatio's utility has two
  near-equal peaks, ~1.15x and the 1.5x cap. With no delay cost, at FAN_S = 0.80 the interior one wins by 0.27% of
  value (framework example; re-checked on the integrated page with the time-to-close, OEWS and SBA-risk fits in), so the
  default recommendation moves from 1.50x to 1.15x. With no delay cost the cap returns for s above about 0.866 (margin
  +0.000008 of value at 0.866, -0.000071 at 0.868; the same on the page before overpricing_time; P(s >= 0.865) = 0.37)
  and, at FAN_S = 0.80, for theta from about 0.763; across 0.75-0.85 the two peaks never differ by more than 0.48% of value.
  With overpricing_time integrated (T_ELAST 0.10, a judgment), at the console default of $900/day the interior peak wins
  by 0.42% of value, the cap returns for s above about 0.90 (flip near 0.904) and for theta from about 0.77 (flip near
  0.7695; the Data tab's "77% kept at $900 a day").
  This is a coin-flip, and the 1.15x end follows from choosing narrowing and applying it to an ask the console sets as a
  multiple of V, which carries no information: under the information reading such an ask faces the whole fan, and the
  whole fan or selection keep the cap. The whole fan, though, misses realisation at typical asks, so neither end is a data
  result. The decision was to ship the narrowed fan everywhere and show the patient-seller price as a range ("close to a
  tie") whenever the other peak is within 1% of value; the tests check the near-tie, not the winner. Option B (not taken)
  would have kept the 1.5x answer by giving bestRatio's candidate asks the whole fan (a `fanShare` argument to
  `fanNodes()`, `model({...s0,ask:V*m,fanShare:1})` inside bestRatio's U()) while the displayed price stays calibrated.
  This replaces the "about 1.57x" note under "Left as documented judgment".
- **Known inconsistency.** The ask ceiling still takes headroom from IBBA's $5M+ ratio (up to 2.6% above the ask),
  which is a ratio to an advisor's benchmark, not to an ask.
- **Data notes.** BizBuySell sector names were harmonised across the 2016-18 tables (15 spellings -> 10 sectors) before
  clustering; IBBA quarters are resampled in calendar blocks (8 quarters are missing inside 2017Q4-2026Q2, no wrap-around);
  IBBA values are whole percentages read off chart labels; the BizBuySell 2018 market table had its price columns swapped
  (a check only).

## Overpricing costs time (T_ELAST), October 2026

`fit/overpricing_time.py` (revision 3), integrated with a different constant than the script recommends.
- **What changed.** Above model value the band median is multiplied by `timeMult(ask, V)` = e^(T_ELAST h), h = ln(ask/V)
  with its first T_SMOOTH = 0.1 rounded (Huber): exactly 1 at or below value, continuous slope at value, log-linear
  above. The band (and the curve's shape) stay keyed on Vbase; the drawn curve, pinned to out.tMed, is rescaled with the
  median. gapPenalty, P_C, the prices and both scores do not read it.
- **T_ELAST = 0.10, a labelled judgment, not an estimate.** The script's chain gives 0.15 (pooled sale-clock
  elasticity 0.52 x P_C at value 0.64, shrunk toward zero). Reviewers showed the two documented ways of converting the
  analogs give about 0.09 (time-given-sale scale; about 0.06-0.07 if only the marketing leg were stretched) and 0.15
  (clock scale); the pooled 95% interval includes zero; and the only Main-Street source (DealLedger, 362 listings,
  31 sales) is uninformative (-0.14, SE 0.55). So the sign comes from
  the analogs (Flippa, Empire Flippers) and the size is set between the two conventions. Stated range 0.05-0.26. Most of
  the analogs' effect rests on Flippa's window hazard, which also counts listings that never sell (already charged by
  Pepperdine's P_C penalty).
- **Optimiser.** `render()` now prices the business score at `bestRatio(s,0,0)`: the proceeds optimum reads neither
  theta nor the cost of delay (it was `bestRatio(s,0,s.lamT)`, identical while time ignored the ask). The note under the
  two listing cards is written by `optNote()` from the optimiser's own delay-inclusive objective: same figure / a lower
  walk-away ask ("the cost of delay pulls the second figure below ... closes sooner") / a higher one ("takes about N
  days longer"). The patient-seller range from the FAN_S step is kept inside optNote (same 1% of value rule, now on the
  delay-inclusive utility). The old note's "Delay cost does not move either" is gone.
- **Effect.** Framework example: 248 days at value, 252 at 1.2x, 257 at 1.5x, 265 at 2x. Walk-away ask (75% kept)
  at $900/day 1.14, 1.14, 1.15, 1.15 for earnings $150k/$400k/$1.45M/$5M (1.15 everywhere with T_ELAST = 0); at
  $4,000/day 1.10, 1.13, 1.14, 1.14. The patient-seller cap returns from about 76% kept with no delay cost, 77% at
  $900/day, 79% at $4,000/day. The script's knife-edge text (cap at $1.45M and $5M, a jump near $736k of earnings) was
  computed before the FAN_S change and no longer applies; the Data tab quotes the integrated page.
- **UI.** "Median time to close" tile tag reads "aggregate × judgment" above value with a live note under the curve
  (band days × multiplier); the eq_ts equation shows t_med = t_band e^(0.10 h); Model III note, provenance line,
  judgment inventory (+2), Fitted-from-public-data row (badged judgment) and the Still-judgement row updated.
- **Tests.** tests/model.test.js section 25 (timeMult exactness, monotone and smooth tMed, exact elasticity above the
  rounding zone, price block untouched, better business never slower, optNote branches, coin-toss and range wording,
  the Data-tab numbers pinned); tests/fuzz.test.js 7f and section 8 (proceeds optimum at lamT 0; walk-away ask optimal
  on the delay-inclusive objective); the curve-independence checks became exact-rescaling checks.

## Competition and the buyer pool (ENG_SHARE), October 2026

`fit/competition_buyers.py` (revision 3), integrated in part.
- **Adopted: the scale.** `ENG_SHARE` = 0.184 (se 0.027, 95% CI 0.13-0.23; 0.164-0.201 across 9 NB specifications)
  replaces the judgment 0.34 in `out.nEng`, `out.nEngRef` and `out.nPool`. An engaged buyer now means one who makes an
  offer, and the scale is calibrated so that a typical pool reproduces IBBA's offers per closed deal by size band
  (25 band-quarter histograms, 2023Q1-Q4 and 2025Q4, about 1,523 closed deals; NB-implied 1.97 / 2.49 / 2.80 / 3.18 / 3.75
  against histogram means of at least 2.00 / 2.30 / 2.78 / 2.83 / 3.83). Stored in `MODELS.fitted.competition` with its
  SE, CI, specification range, the band offers tables, the 2023Q4 / 2025Q4 series disagreements and `refit_when`
  (refit whenever `IND` buyers, the BUYERS fit functions, peRef or buyerMix change).
- **Premium unchanged.** `COMP_H` = 3 x ENG_SHARE / 0.34 = 1.62 re-expresses the old half-saturation in offers, so
  `compPrem` equals the old kappa ln((3+0.34x)/(3+0.34x_ref)) to 1e-12. `COMP_K` = 0.03 stays judgment (IBBA's
  within-band panel bounds it only to -0.33..+0.31; neither 0 nor 0.03 predicts held-out quarters better).
- **Not adopted: the negative-binomial thin-pool factor** (a blocking review). Its level rests on the zero-offer class,
  which IBBA never observes (the histograms are of closed deals): under $500K the NB gives a typically marketed listing a
  0.50 chance of any offer (Poisson-lognormal 0.57), below Pepperdine's 0.61 close rate. The thin-pool factor keeps the
  Poisson shape, `(1-e^-nPool)/(1-e^-nEngRef)`, now at the calibrated scale ("calibrated scale, judgment shape"). The
  cost: under the Poisson the same expected offers imply 1.6-3.0 offers per closed deal, below IBBA's. `nb_r` is metadata.
- **Smooth cap.** The hard `min(1, .)` is replaced by `capOne()`: the ratio itself up to 1 - THIN_W (0.05, judgment),
  exactly 1 from 1 up, a quintic (C2) blend between. Monotone, never above 1, lifts the ratio by at most 0.014, exactly
  1 at a typical pool or deeper (so peers in the Omni score and every result at or above a typical pool are unchanged),
  and no kink for the sensitivity panel's central difference to straddle. A smooth cap equal to 1 at the typical pool
  within 1e-3 cannot also round the corner symmetrically (`softMinR(raw,1)` is 0.992 there), hence the one-sided blend.
- **Effect.** Below a typical pool P_C falls further: half the typical pool scales it by 0.58-0.85 (was 0.65-0.96;
  0.56-0.89 across the ENG_SHARE CI), a quarter by 0.31-0.60 (was 0.37-0.80). Framework example (medical, $1.45M SDE,
  typical 50): at 25 buyers thinF 0.90 -> 0.77, P_C 0.61 -> 0.52, Omni score 27 -> 2; at 40 buyers 40 -> 33; at
  50 and 65 unchanged (43). Median businesses (16 industries x SDE $0.2M/$1M/$4M) at half the typical pool score 1-25
  instead of 1-43 (median drop 21), at three quarters 19-43 instead of 27-48. The score moves more than P_C because peers
  are all marketed to a typical pool; it rests on the judgment typical pool `IND` buyers (example at 40 buyers: 43 / 33
  / 27 for a typical pool of 40 / 50 / 60). The 'Qualified buyer pool' sensitivity row is positive everywhere and
  changes smoothly through the typical pool (dP 0.032 / 0.028 / 0.023 at 48 / 50 / 52 buyers). Round 5 replaced that
  central difference with the step the row names, 25% more buyers from the current pool, which is zero for P_C at a
  typical pool or deeper (R5-2).
- **Unchanged (judgment):** BUYERS mf / syn and PHI. The Pepperdine 2016 / 2025 strategic-over-financial premium (pooled
  13.7%, se 3.1) against the model's 10.7% with both present, GF Data's add-on / platform 1.08 against 1.09, and Stanford
  2024 are stored as a consistency check (`strategic_premium`, `addon_over_platform_gf`) and shown in the Data tab.
- **Data tab.** New Fitted-from-public-data row (badged calibrated, numbers read live from `MODELS.fitted.competition`,
  the score effect labelled as at integration); the Still-judgement rows for kappa / thin-pool shape and for the buyer
  archetypes rewritten; the IND judgement row names the typical pool; nFit +1 (ENG_SHARE), nJudg +1 (THIN_W).
- **Tests.** tests/model.test.js section 26 (metadata, the model never reads nb_r or the PLN scale, capOne monotone /
  exact / kink-free, the IBBA calibration at the five band centres, stored ranges and score pins regenerated from the
  live build, compPrem identical to the old formula, the IND.buyers sensitivity pin, the sensitivity row, BUYERS
  unchanged with the strategic premium in [0.08, 0.18]); tests/fuzz.test.js 7g (thinF in (0,1], exactly 1 from the
  typical pool, within the cap's lift of the Poisson ratio, no quality input; P_C, thinF and expected proceeds never
  fall as buyers rise; premium identical). The judgment-inventory regex now expects `+ 2 + 1`.

## Quality weights checked against online-business sales, October 2026

`fit/quality_weights_v2.py` (revision 2), integrated as metadata and text only. **No weight moves**: owner dependence
1.24 and management depth 0.60 stay; the other seven keep weight 1. Model output is bit-identical (400 random
businesses, 0 of 28,000 numeric fields differ).
- **Growth.** A positive direction appears in Empire Flippers sale prices (positive in all 39 EF specifications and out
  of sample), driven mainly by declining businesses being discounted: against the middle fifth of growth the two
  shrinking fifths sell at multiples 13% and 6% lower, the two fastest-growing fifths within 3% (EF's own 2021 tables on
  listed earnings: declining -10% vs stable, growing -2%, not significant). Growth above zero adds little. The weight
  relative to the other dimensions is not identified (0.60-0.94 of an equal share on twelve-month windows, 2.59 re-based
  to trailing earnings, partly mechanical; 0.09-2.59 across bases and units; ratio 1.32 [0.27, 3.55]).
- **Recurring revenue.** The asking-price premium is significant (EF last ask 0.42, se 0.16; Flippa final asks 2.17,
  se 0.84); the sale-price premium is not (EF 0.17, se 0.24; Flippa auctions -1.92, se 2.13); and the difference between
  them is not significant either (EF sale minus ask -0.25, se 0.17). The fit's wording "a premium in asking prices only,
  none in sale prices" was not adopted, on review.
- **Management depth** is marked weak (`weak: ["mgt"]`, `weak_note`): no out-of-sample value in broker listings, ratio to
  the other measured dimensions 0.99 [-0.11, 3.13]. The settled 0.60 is kept, not re-decided.
- **Metadata.** `MODELS.fitted.quality_weights` gains `fitted`, `weak`, `weak_note`, `judgment` and `checked` (the
  evidence the Data tab quotes, plus `grw.ef_quintiles`, `grw.ef_report_decreasing_vs_stable` and `mgt` added at
  integration); `QW` reads none of it. `MODELS.value.quality_band.weighting` now describes the weighted composite.
- **UI.** Quality note under the band and the "what the sliders move" note ("no reachable data identifies their relative
  weight"); Quality-positioning table (management depth weak; the judgment row quotes the online-sales evidence, numbers
  read live from `checked`); weak-proxy note; Fitted-from-public-data quality-weights row (management depth weak, rec and
  grw checked, no change); Still-judgement status. No fitted-parameter row is added; the counts are unchanged.
- **Tests.** tests/model.test.js section 27 (the fit's quality_weights.test.js folded in, with the recurring-revenue
  check changed from "sale minus ask < 0" to "the difference is not significant", plus the growth-shape checks, the
  banned wording and the rendered evidence template); tests/fuzz.test.js 7h (qz is the signed weighted z over the norm;
  QW reads only the fitted weights; growth moves qz by w/norm).

## Logic audits (rounds 0 to 5) and the time-to-close median refit, October 2026

### How the audits ran

Each round worked from a frozen copy of the page at one commit:
- **Find.** Independent auditors each took one area, and every finding had to carry a numeric reproduction: the exact inputs and the numbers they produced.
- **Verify.** Two verifiers judged every finding. One tried to reproduce it with their own commands; the other tried to refute it. A refutation could show the behaviour was intended and labelled, already documented, mis-measured, or immaterial.
- **Confirm.** A finding counts as confirmed only if it reproduced and was not refuted.
- **Fix.** Confirmed findings were fixed in one batch and pinned by tests.
- **Repeat.** The next round started from the fixed page and was told what had already been raised, fixed or rejected (with the reason), so it looked for what earlier rounds missed and for anything the fixes broke.

Full verdicts, reproductions and rejections are in `AUDIT_FINDINGS.md`.

| Round | Commit audited | Raised | Confirmed | Rejected | Fixed in |
|---|---|---|---|---|---|
| 0 | 7cac297 | — | 25 (17 distinct) | — | a6d235c |
| 1 | a6d235c | 51 | 34 | 17 | c27ebf1, 1084036, 549537e |
| 2 | 0f1fa9b | 25 | 16 (11 distinct) | 9 | df83852, 3d53b6f |
| 3 | 3d53b6f | 20 | 11 (9 distinct), plus 1 reproduced by hand where the verifiers returned no verdict | 8 | 39842b1 |
| 4 | a7346a7 | 7 (2 of 4 auditors finished) | 7 verified by hand, plus 1 from a hand-run numbers pass | 0 | f3c3f87, 79a18c0 |
| 5 | 706a61c | 12 (4 auditors; the invariants auditor found nothing) | 9 (7 distinct; 2 medium) | 3 | eec0ddd |

### What changed

**Decisions**
- The cost of delay is charged on the mean time to close, E[T], not the median.
- The 2% floor that froze P_C far above value is gone.
- The business score is priced at the proceeds-optimal ask and at least a typical buyer pool.
- Each buyer closes on the gap between the ask and its own value V_j, and is paid at most the ask ceiling (R1-4, R1-5). The equation, the table and "pays most" show that cap (R2-1).
- **The fan's anchoring now stops where the documentation always said it did (R2-2).** Each fan slice used to anchor on the raw ask against its own W, so E[P | close] kept rising about 2% between 1.5× and 2× value, the region bestRatio refuses to search. Every slice now anchors on the effective ask softmin(ask, 1.5 V), the same quantity the ceiling reads.
  - The effective ask differs from the ask by under 1e-9 below 1.2× value and by about 2e-6 at 1.35×. (Commit df83852's message calls asks below about 1.4× "bit-identical", which overstates it.)
  - The optimiser no longer keeps an ask above 1.5× a programme's value.
  - Near-cap figures moved: the interior peak wins by 0.55% of value (was 0.48%), the theta flip is 0.776 (was 0.772), the FAN_S flip 0.94 (was 0.92), the PEN_MAX flip 0.42 (was 0.43), and the patient-seller cap wins from 77% / 78% / 81% kept (was 76% / 77% / 81%).
  - Walk-away asks at the quoted precision are unchanged.

**Optimiser and table texts**
- optNote, optCardNote and the sensitivity note describe the numbers they sit beside: term directions, the coin-toss rule at 1% of value, the delay cost in dollars, and the ask-binding share.
- The intervention table's net days use E[T].

**Provenance**
- Badges switch to "× judgment" where a judgment factor acts: the quality position on value and the multiple, PEN_MAX and the size ramp on P_C, the SBA tail factor on risk, and overpricing on time.
- The time tile now reads "fitted".
- The three tallies are counted from the tables themselves: fitted 537, aggregate 38, judgment 432 at 79a18c0.
  - These ledger rows read their own definitions (R2-9, R3-4, R4-2, R4-7):
    - BUYERS (54) and INTERV (43);
    - the judgment multiple stack (68);
    - category (38) and confidence (8);
    - quality-dimension peer scales (19) and size and buyer-pool scales (3).
  - The note under the ledger is computed from the rows: 124 of the 432 are inert, counting the `IND` anchors and the judgment bounds PMIN, PMAX, LAM0 and KW, which reach only the unused judgment panels (R4-4, R5-1).
  - The aggregate count includes IBBA's cash at close and DealStats' deal structure, but not the prime rate, which moves no figure (R2-8, R3-2).
  - The masthead and footer no longer call timing an aggregate (R2-10, R3-1).
- P_C is described as having no quality term, reached by quality only through the gap.

**Equations**
- Every eq_* general form now reproduces the substituted line beneath it:
  - the hinge definition above $3M of SDE;
  - the gap-tail rate to three significant figures;
  - the median calibration and quality position in eq_vs;
  - the stack bounds;
  - the softmin cap in eq_a and eq_b.

**Data-tab claims computed live**
These were hand-typed and had gone stale:
- the termination trend, generated from the series;
- the DealStats cross-check (r = 0.46 on the eight tabulated sectors, not the old 0.887);
- the SBA loan-size reversal;
- the walk-away and knife-edge figures;
- the LOI-leg share (40%, 32–43% by band) and the marketing-leg conversion of T_ELAST (0.05–0.06).

**Display and texts (round 3)**
- `money(x,0)` kept no decimals in millions, so $1.30M of costs showed as "$1M" and a $1.5M budget as "$2M"; it now keeps two (R3-6).
- The star-map tooltip shows the price at this ask (R3-7).
- The printed point-estimate anchoring reads the effective ask, as the fan does (R3-8).
- The SBA loan-size gap is described at the hazard pieces' start ages: larger loans are charged off less often through month 72 (×0.26 per tenfold at 6 months, rising to ×0.89 in months 60–72) and more often from it (×1.16); it is not "closing at 5.4 years" (R3-5, R5-7).
- The TermInMonths leak is measured on the hazard model's own loans by the new `fit/sba_term_trap.py`: 84% of paid-in-full loans carry a standard term against 11% of charged-off ones, and the field alone gives AUC 0.825. The old figures (86.9%, 13.0%, AUC 0.957) came from the superseded logistic (R3-9).
- Pepperdine's resolved termination range is read from the series: 33–41% (R3-10).

**Round 4**
- `TermInMonths` is not the time to charge-off (within 3 months for 2.5% of charged-off loans), so the page no longer says SBA overwrites it with that.
- The Census head count runs from about a fifth of SBA's jobs count to about six times it for loans within the $5M 7(a) limit, at each industry's typical margin; it is more at lower margins (a $10M staffing firm at a 10% margin is 11×), and keeps growing with revenue past the limit, where SBA's band median stays at 14. It is not "several times fewer" (R4-3, R5-6, R6-2).
- The GM salary's firm-size rank is labelled judgment.
- The budget box shows two decimals in millions.
- The binding-ask note names the measure it ranks by.

**Round 5**
- The sensitivity panel's ask and buyer-pool rows show the step they name, a 5% lower ask and 25% more buyers, from the current state. The central difference they used straddled the proceeds peak and the typical pool: at the recommended ask it showed +$51k for a 5% cut that the model prices at −$34k (R5-2).
- The competition premium's dollar figure at the point estimate goes through the ask ceiling, as P(W) does; it overstated the effect by up to 4× just short of the median binding (R5-3).
- The judgment ledger counts the `IND` anchors and PMIN, PMAX, LAM0 and KW as inert: 124 of 432, not 104 (R5-1).
- The Data tab computes the old judgement build's swing (1.47× to 6.06× on the framework example, against 1.75× to 3.17× for the console's multiple, all of it the judgment quality position on the fitted 2.41×; R6-1) and the owner-pay share of SDE (37–64% at $200K, 18–58% at $3M), instead of typing figures the model contradicts (R5-4, R5-5).
- The staffing comparison is scoped to the $5M 7(a) limit (R5-6), and two lines of this section are corrected (R5-7).

**Competition**
- The held-out benchmark is labelled correctly: a Poisson at its own refitted scale (0.255).
- The pairing the thin-pool factor actually uses (Poisson shape at the NB's scale) is now scored: −1.778 per deal, no better than the old 0.34 judgment (−1.773). So the scale is calibrated and the shape stays judgment (`fit/competition_heldout_poisson.py`).

**Time-to-close band medians: fitted (`fit/time_to_close_medians.py`)**
- **Method.** They were IBBA's published 2018–23 lookup. They are now maximum-likelihood medians of the interval-censored log-logistic, fitted with the shipped shape to the same per-band histograms (15 quarters, 4,533 closed deals). Each band is shrunk toward a line in ln(deal size).
- **Values.** 6.54 / 7.75 / 8.02 / 9.03 / 10.14 months listing to close; 2.12 / 3.06 / 3.20 / 3.87 / 4.05 LOI to close.
- **SEs.** Quarter-bootstrap, with half the rounded-against-truncated month gap (0.5–0.6 months) added in quadrature.
- **Out of sample.** The shipped pipeline (shrunk in each fold, rounded) beats the published medians:
  - listing +0.0028 nats per deal (SE 0.0012), better in 12 of 15 held-out quarters;
  - LOI +0.0126 (SE 0.0035), 13 of 15;
  - both better in 4 of 4 quarters when fitted on 2020–22.
- **Calibration against the histograms.** The largest gap in the share closed falls from 9.4 to 3.0 points at 180 days and from 6.9 to 4.7 at 365 days.
- **Remaining size-order quirk.** The share closed after about 18 months still rises with size between $250k and $707k, now by at most 0.7 points near 900 days (was 1.4). This comes from the wider under-$500K shape.
- **Effect on the framework example.**
  - The median time to close at value goes from 248 to 277 days and E[T] from 318 to 355; the share closed by day 180 falls from 30% to 24%.
  - The proceeds-optimal ask (1.10×) and the walk-away ask (1.15×) are unchanged.
- **Self-audit.** The BizBuySell days-on-market row now reads off (213 days against 170 ± 40; 207 with the published medians). The row says this is a disagreement between IBBA and BizBuySell, rather than widening its window. With this row, three self-audit rows read off.

### What remains judgment, and why

Each item is on the Data tab's "Still judgement" ledger with the data that would fit it. None can be fitted from anything reachable here.

| Component | Why it is not fitted |
|---|---|
| **Quality position (qFactor) and the judgment stack's bounds** | No dataset records the soft variables (owner dependence, recurring revenue, concentration, …) per closed deal. Listing text priced only owner dependence and management depth, and those weights are shrunk toward 1. |
| **Anchoring strength α = 0.55, ceiling A_max = 1.30** | Sale-to-ask data identify (1−α)·s, not α: with s refitted, every α from 0.30 to 0.85 gives the same realisation level. Fitting α needs asks that vary for reasons unrelated to the business. |
| **PEN_MAX = 0.45, the $1M–$5M base-rate ramp, and the >50% bucket's placement** | Pepperdine publishes where price-killed deals died and base rates by channel, not a response of P_C to the gap or a base rate by size. These are load-bearing: below 0.42 the framework example's walk-away ask jumps to the cap. |
| **T_ELAST = 0.10 (time cost of overpricing)** | The sign is fixed by online-marketplace analogs. The Main-Street size is not identified: DealLedger has 31 sales, and the pooled 95% interval includes zero. |
| **Competition premium κ = 0.03 and the thin-pool factor's shape and cap** | IBBA's histograms are of closed deals, so the zero-offer class is never observed. Its band averages bound κ only to −0.33..+0.31. |
| **FAN_S = 0.80 and ENG_SHARE = 0.184** | *Calibrated*, not estimated. Each is set to reproduce a market average (sale-to-ask; offers per closed deal), and neither mechanism is identified. They are counted in no tally. |
| **Buyer archetypes, φ, strategic premium** | Who bought what at what premium is unpublished. The size mix is fitted; the multiple factors are only checked, against Pepperdine 2016/2025 and GF Data. |
| **SBA tail factor ×1.20 (years 9–10)** | No change-of-ownership loan is older than 8.5 years (SBA has flagged them only since Dec 2017). |
| **Intervention costs, durations and effects; category sub-score weights; the confidence formula** | They need before/after records of pre-sale changes, or an outcome to predict. Nobody publishes either. |
| **GM firm-size rank and the e-commerce wage bridge** | OEWS has no wages by firm size and no e-commerce row since NAICS 2022. |
| **IND typical buyer pools** | They set the reference for the thin-pool factor and the competition premium; no source counts buyers contacted per listing. |

### Where the audit loop stands, and the dated sections above

- **Rounds.** The confirmed defects fell from 25 and 34 (rounds 0–1) to 11, 10, 8 and 7 (rounds 2–5).
- **Remaining defects are textual.** After round 2 they are almost all low-severity wording and count defects; the one medium was R3-6's rounding of millions.
- **No defect since round 2 has changed a model output** (value, prices, P_C, time, risk, proceeds, the recommended asks or the scores).
  - Round 3's R3-6 and R3-8 corrected how figures were displayed: rounding of millions, and the printed point-estimate anchoring factor.
  - The rest are wording and count defects.
  - Round 4's value auditor found only a ledger count, and the hand-run numbers pass (about 14,240 checks across 33 states) found one ambiguous sentence.
  - Round 5's two medium findings were display computations: the sensitivity panel's ask and buyer-pool rows, and the competition premium's dollar figure. The rest were typed figures and counts.
- **The loop is not formally closed.**
  - Round 4 lost its claims and numbers auditors and both verifiers to the subagent usage cap. Round 5 re-audited the claims and numbers with full two-lens verification and confirmed 7 defects, so a sixth round is reviewing the round-5 fixes, the arithmetic the render code does itself, and the figures typed into prose.
- **The dated sections above are records at the time of integration.** On the shipped model, for the framework example:
  - the median time to close is 277 / 281 / 287 / 295 days at 1 / 1.2 / 1.5 / 2× value (248 / 252 / 257 / 265 before the median refit);
  - the walk-away ask (75% kept) is 1.13 / 1.14 / 1.15 / 1.15 at $900 a day and 1.09 / 1.12 / 1.14 / 1.14 at $4,000;
  - the patient-seller cap wins from 77% kept with no delay cost, 78% at $900 a day and 81% at $4,000;
  - the FAN_S flips are 0.88 and 0.94;
  - the Omni score at 25 / 40 / 50 / 65 buyers is 1 / 31 / 41 / 41, and at 40 buyers with a typical pool of 40 / 50 / 60 it is 41 / 31 / 25;
  - three self-audit rows read off, not two.

### Tests

At HEAD:
- `node tests/model.test.js`: 7,465 checks. Section 29 pins the round-0 fixes, 30 round 1, 31 the median refit, 32 round 2, 33 round 3, 34 round 4 and 35 round 5.
- `node tests/fuzz.test.js 1500`: 173,364 checks. Invariants 7i–7p cover:
  - E[T];
  - P_C monotone in the ask with no floor;
  - buyer EV = P_E·P_C,j·P_j;
  - the SBA rate;
  - outreach;
  - the score pool;
  - the optimiser texts;
  - the fitted medians (monotone, continuous, reading only deal size, moving only time outputs);
  - the flat price past the cap.

  The optimiser never keeps an over-cap ask.
- `node tests/browser.inputs.js` and `node tests/browser.sweep.js` (118 input states at 1440px and 390px): pass.
