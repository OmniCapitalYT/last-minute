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
  at that edge, or in the soft cap's rounded corner from the printed 1.44×, is
  labelled "test the market", and the note says when the two
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
  `fit/time_to_close_medians.py`; see "Logic audits (rounds 0 to 7) and the time-to-close median refit, October 2026" at the end of this file.
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
  tie") whenever another peak is within 1% of value (every such peak, since the sixth skeptic round of the broker tools); the tests check the near-tie, not the winner. Option B (not taken)
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

## Logic audits (rounds 0 to 7) and the time-to-close median refit, October 2026

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
| 6 | eec0ddd | 8 (3 auditors) | 4 (3 distinct, all in round-5 fix text) | 4 | ba01aba |
| 7 | 9d7e9d9 | 1 (1 auditor, closing check of the round-6 fixes) | 1 (the staffing sentence again) | 0 | 268e4b6 |

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
- The Census head count runs from about a fifth of SBA's jobs count for a small firm to many times it for a low-margin or lower-quality one (a $10M staffing firm at a 10% margin is 11×; a typical-margin restaurant at the worse quality ends is 10.6×), and keeps growing with revenue past the $5M limit, where SBA's band median stays at 14. The page states the mechanism rather than a bounded range, because every bound tried failed along another input (R4-3, R5-6, R6-2, R7-1). It is not "several times fewer".
- The GM salary's firm-size rank is labelled judgment.
- The budget box shows two decimals in millions.
- The binding-ask note names the measure it ranks by.

**Round 5**
- The sensitivity panel's ask and buyer-pool rows show the step they name, a 5% lower ask and 25% more buyers, from the current state. The central difference they used straddled the proceeds peak and the typical pool: at the recommended ask it showed +$51k for a 5% cut that the model prices at −$34k (R5-2).
- The competition premium's dollar figure at the point estimate goes through the ask ceiling, as P(W) does; it overstated the effect by up to 4× just short of the median binding (R5-3).
- The judgment ledger counts the `IND` anchors and PMIN, PMAX, LAM0 and KW as inert: 124 of 432, not 104 (R5-1).
- The Data tab computes the old judgement build's swing (1.47× to 6.06× on the framework example, against 1.75× to 3.17× for the console's multiple, all of it the judgment quality position on the fitted 2.41×; R6-1) and the owner-pay share of SDE (37–64% at $200K, 18–58% at $3M), instead of typing figures the model contradicts (R5-4, R5-5).
- The staffing comparison is scoped to the $5M 7(a) limit (R5-6), and two lines of this section are corrected (R5-7).

**Round 6** (all three in text the round-5 fixes wrote)
- The quality-sweep sentence credits the swing to the judgment quality position, not to the fitted multiple, which the sliders do not move (R6-1).
- The staffing range is stated at each industry's typical margin, and is larger at lower margins (R6-2; round 7 replaced the range with the mechanism, R7-1).
- eq_comp's general form is the capped price P(W), as in eq_a; the substituted line says which figure is before the ceiling and which after it (R6-3).

**Round 7** (closing check)
- The staffing sentence states the mechanism instead of a bounded head-count range. Each range given (R4-3, R5-6, R6-2) had failed along another input: the loan cap, then the margin, then quality (R7-1).

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

Each item is on the Data tab's "Still judgement" ledger with the data that would fit it. None of the rows not struck through can be fitted from anything reachable here. The struck row was fitted in the second round (October 2026, below) from the same SBA files, once rewritten loan terms could be classified; rows marked October 2026 had parts read from public data.

| Component | Why it is not fitted |
|---|---|
| **Quality position (qFactor) and the judgment stack's bounds** | No dataset records the soft variables (owner dependence, recurring revenue, concentration, …) per closed deal. Listing text priced only owner dependence and management depth, and those weights are shrunk toward 1. |
| **Anchoring strength α = 0.55, ceiling A_max = 1.30** | Sale-to-ask data identify (1−α)·s, not α: with s refitted, every α from 0.30 to 0.85 gives the same realisation level. Fitting α needs asks that vary for reasons unrelated to the business. |
| **PEN_MAX = 0.45, the $1M–$5M base-rate ramp, and the >50% bucket's placement** | Pepperdine publishes where price-killed deals died and base rates by channel, not a response of P_C to the gap or a base rate by size. These are load-bearing: below 0.42 the framework example's walk-away ask jumps to the cap. |
| **T_ELAST = 0.10 (time cost of overpricing)** | The sign is fixed by online-marketplace analogs. The Main-Street size is not identified: DealLedger has 31 sales, and the pooled 95% interval includes zero. |
| **Competition premium κ = 0.03 and the thin-pool factor's shape and cap** | IBBA's histograms are of closed deals, so the zero-offer class is never observed. Its band averages bound κ only to −0.33..+0.31. |
| **FAN_S = 0.80 and ENG_SHARE = 0.184** | *Calibrated*, not estimated. Each is set to reproduce a market average (sale-to-ask; offers per closed deal), and neither mechanism is identified. They are counted in no tally. |
| **Buyer archetypes, φ, strategic premium** | Who bought what at what premium is unpublished. The size mix is fitted; the multiple factors are only checked, against Pepperdine 2016/2025 and GF Data. *Since October 2026 the individual's factor is calibrated (0.97); see the second round below.* |
| ~~**SBA tail factor ×1.20 (years 9–10)**~~ | *Fitted since October 2026*: ×1.21 (SE 0.06) from mature 7(a) loans, read by the note's size (second round, below). Still carried over, not observed: no change-of-ownership loan is older than 8.5 years. |
| **Intervention effects and durations, the costs no benchmark covers; category sub-score weights; the confidence label's cut-offs** | They need before/after records of pre-sale changes, or an outcome to predict. Nobody publishes either. *Since October 2026 the QoE fee, the GM's loading and hire, the sales hire's floor and the confidence figure itself are read from public data (second round, below).* |
| **GM firm-size rank and the e-commerce wage bridge** | OEWS has no wages by firm size and no e-commerce row since NAICS 2022. |
| **IND typical buyer pools and strategic interest** | They set the reference for the thin-pool factor and the competition premium, and the strategic share; no source counts buyers contacted per listing or the strategic share of small-business buyers (checks in `MODELS.fitted.peer_checks`). |

### Where the audit loop stands, and the dated sections above

- **Rounds.** The confirmed defects fell from 25 and 34 (rounds 0–1) to 11, 10, 8, 7, 3 and 1 (rounds 2–7).
- **Remaining defects are textual.** After round 2 they are almost all low-severity wording and count defects; the one medium was R3-6's rounding of millions.
- **No defect since round 2 has changed a model output** (value, prices, P_C, time, risk, proceeds, the recommended asks or the scores).
  - Round 3's R3-6 and R3-8 corrected how figures were displayed: rounding of millions, and the printed point-estimate anchoring factor.
  - The rest are wording and count defects.
  - Round 4's value auditor found only a ledger count, and the hand-run numbers pass (about 14,240 checks across 33 states) found one ambiguous sentence.
  - Round 5's two medium findings were display computations: the sensitivity panel's ask and buyer-pool rows, and the competition premium's dollar figure. The rest were typed figures and counts.
  - Round 6 found only wording in round 5's own fixes; its auditor of the arithmetic the render code does itself had all four findings refuted.
  - Round 7 found one: the same staffing sentence, along a third input.
- **Where the loop stopped.**
  - Round 4 lost its claims and numbers auditors and both verifiers to the subagent usage cap. Round 5 re-audited the claims and numbers with full two-lens verification and confirmed 7 defects; round 6 confirmed 3, all in round 5's own fix text; round 7, a closing check of those fixes, confirmed 1.
  - The loop stops at round 7. Its one finding was the same sentence again, and the fix states no bound, so it has no further input to fail along. The last two rounds found nothing outside the previous round's own fix text, and no figure the model computes has been wrong since round 2.
- **The dated sections above are records at the time of integration.** On the shipped model, for the framework example:
  - the median time to close is 277 / 281 / 287 / 295 days at 1 / 1.2 / 1.5 / 2× value (248 / 252 / 257 / 265 before the median refit);
  - the walk-away ask (75% kept) is 1.13 / 1.14 / 1.15 / 1.15 at $900 a day and 1.09 / 1.12 / 1.14 / 1.14 at $4,000 (1.08 / 1.12 / 1.14 / 1.14 since the October 2026 second round);
  - the patient-seller cap wins from 77% kept with no delay cost, 78% at $900 a day and 81% at $4,000;
  - the FAN_S flips are 0.88 and 0.94;
  - the Omni score at 25 / 40 / 50 / 65 buyers is 1 / 31 / 41 / 41, and at 40 buyers with a typical pool of 40 / 50 / 60 it is 41 / 31 / 25;
  - three self-audit rows read off, not two.

### Tests

At HEAD:
- `node tests/model.test.js`: 7,468 checks. Section 29 pins the round-0 fixes, 30 round 1, 31 the median refit, 32 round 2, 33 round 3, 34 round 4, 35 round 5 and 36 round 6.
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

## UI upgrade (Phase 4), October 2026

The brief: "more premium, not busier", with "tons of space-themed elements, vibrant colors, and universe visuals", keeping every space element, the palette, the intro animation and the warp transitions, and never changing a number or the meaning of any text.

### How it ran
- **Before.** Every section of both tabs was screenshotted at 1440 and 390 px (44 images) at 706a61c.
- **Round 1 critique.** Three critics (layout, typography and consistency, premium space aesthetic) went through every screenshot and measured the live page. Their 267 findings were merged into 120 issues (18 high, 67 medium, 35 low) and a shared visual language: per-section hue pairs and planets, glow and texture recipes, one type, spacing and radius scale, a table contract and a reveal hook. Four high-severity themes: phones hid the numbers (wide tables scrolled twice or pushed figure columns off-screen, chart text rendered at 3–5 px, 19 of 33 equations shrank to 6.9 px and still clipped); outright defects (score-dial moons 90° from their arcs, KPI labels at 2.8–3.9:1 contrast from stacked opacity, invisible slider focus); no system (36 font sizes, nine radii, six small-label styles); and section identities that never reached the screen.
- **Round 1 implementation.** Four lanes worked in parallel git worktrees, each owning one region: hero and the shared layer, charts, the console sections, and the Data tab. All 120 issues were addressed (four partially: see below) and every upgrade plan was implemented. Each lane is one squash-merge commit: a2fd636 (Data tab), c6345e8 (console), 4b0a7a8 (hero and shared layer), 8221fb1 (charts); f8e8c01 fixes a cross-lane custom-property clash. The four merged without conflicts, and the merged build passed every test.
- **Round 2 (light, by the owner's choice to finish by 1 PM ET).** One reviewer checked the merged page for regressions and for round-1 high or medium issues that persist, and the fixes were applied directly. It found no round-1 high or medium issue still present (all 18 round-1 highs confirmed fixed, measured) and three medium regressions: a scroll chevron with nothing to scroll that kept animating even under reduced motion, the new sticky tab bar able to cover a control that keyboard focus scrolls into view, and phone lede clamps that hid a single line and cut a word. All three are fixed in 4e0010a and verified in the browser. Low-severity polish was out of this round's scope (subscripts and inline code render at 8–10 px; Data-tab section heads sit flush with the panel edge where Console heads are inset).

### What changed, by area
- **Shared layer:** tokens for hue, ink, type, spacing and radius; a chip primitive; provenance dots in their tier colours; star-plate equation cards; one table contract (`.wide` with a sticky first column, `.cards` that stack into labelled cards on phones, scroll-aware fades); one `details.more` disclosure; a guarded reveal hook. Nothing animates under `prefers-reduced-motion`.
- **Masthead and hero:** a planet-limb horizon that the sticky tab bar docks on (tabs above the fold on a phone); the hero in three tiers (planet beside the two dials, which now end exactly at their arcs; calibration band and quality bar; the KPI grid at 10.6:1 label contrast).
- **Section identity:** each section has a hue pair, a recoloured waypoint planet, an orbit rule and a glyph emblem; nebula washes stay inside the glass at no more than 10% so text contrast is unchanged.
- **Charts:** every chart is drawn at its displayed size with all text at 11 px or more on both widths; the star map is a sky with collision-free labels; the time curve carries a comet at the median; star-track bars; the focal planet's percentage always matches its tile.
- **Console sections:** key-figure strips lead each section; equations re-stack one term per line on phones instead of shrinking (smallest equation text 12.3 px); tables become cards on phones; the optimiser's sell-or-walk-away choice is a binary-star card; spectral scenario cards; 40 px tap targets in the rail.
- **Data tab:** a tier planet and hue per section; a stellar-spectrum tally; the Still-judgement table (4,289 px wide before) reads in three columns; check rows aligned to 1 px; self-audit rows with verdict chips and gauges; a star-chart index in the right gutter on wide screens.

### Not done, or done partly
- r1-data-02: three of 25 check rows are still 201–250 px tall at 390 because of text length; folding would not get them under 140 px.
- r1-data-14: the optional sticky side column for long notes was not built; long notes keep their first sentence and fold the rest.
- r1-hero-18: the second KPI row is 238 px tall at 1440 (293 before; the target was 180) because its definition lines must stay visible.
- r1-hero-06: two pairs of adjacent sections differ by about 3 colour levels at the panel corner rather than 4, the most the 10% wash cap allows; their rims, rules, planets and emblems still differ.
- The full critique loop ("until a round finds nothing new") was cut to one light round at the owner's request, so low-severity polish was not re-reviewed after round 1.
- Before and after screenshots of every section at both widths were taken at 706a61c and 4e0010a; they are working files, not committed.

### Tests
At the merged head: `node tests/model.test.js` 7,468 pass; `node tests/fuzz.test.js 1500` 173,364 checks pass; `node tests/browser.inputs.js` and `node tests/browser.sweep.js` (118 input states at 1440 and 390 px, no horizontal overflow, no NaN): pass. No test was changed by the UI work.

### Round 2 (full) and the closing check
At the owner's request the full loop ran once more, aimed at making the page "even more brilliant and stunning", time-boxed to about three hours.
- **Critique.** Three critics (layout, typography, and a brilliance lens) re-checked every section at 1440 and 390 px against the round-1 and light round-2 issues. Their 50 findings merged into 49: one high (the wide-table "scroll" chip covered the Model III header on phones), 16 medium, 32 low, and 19 brilliance ideas ranked by impact against risk. Nine earlier issues persisted, three were regressions.
- **Implementation.** Four lanes, one squash-merge each: 756b62d (console: lit answer capsules, key-figure halos with a one-time glint, scenario cells lit in their own colour, a slider gravity ring while dragging, one pulse along the value-gap arc, a centred footer with a lit rim), 910479d (charts: a terminator and rim light on the focal planet, a one-shot draw and comet head on the time curve, stellar cores and a beacon on the pursue-first star, zero meridians), 1aa79a1 (hero and shared layer: starlight section titles, a smoked-glass tab bar with a travelling comet, a one-time light band through the masthead title, the solar system drawn to the phone's width, focus halos, KPI star trails), f726455 (Data tab: tier waypoint stars and nebulae, observatory plates in the empty gutters on wide screens, tally halos). All 49 issues were addressed; one optional fade was dropped because it would play off-screen. Visible text now spells "judgment" and "optimizer" consistently; the one pinned "judgement" sentence is unchanged. No number or claim changed.
- **Closing check (round 3).** One reviewer found no high issue, no round-2 issue still visible, nothing animating under reduced motion and no text below WCAG AA in a scan of about 2,200 text runs, and two medium regressions on the first phone screen (the status labels ran together; the tab bar sat 3 px under them). Both are fixed in 01cc3fe; narrow phones (375–383 px) keep a two-row status layout so no label wraps.
- **Tests at 01cc3fe:** `node tests/model.test.js` 7,468 pass; `node tests/browser.inputs.js` and `node tests/browser.sweep.js` (118 input states at 1440 and 390 px) pass. No test was changed by the UI work.
- **Left as is:** low-severity polish beyond the closing check's scope; the four partial round-1 items listed above.

### Final verification after the UI work
A last round on the finished build (55d0c17), recorded in AUDIT_FINDINGS.md: a numbers auditor found every figure on both tabs equal to the model in more than ten varied states, including every figure the UI work repeats; a claims auditor's one confirmed finding was the optimizer card folding away the walk-away price's "range / close to a tie" and "test the market" qualifiers (the note is no longer folded); a fresh-eyes UI review found an invisible Tab stop, the focal label overhanging the planet on phones and a reference pill past the phone gutter. All fixed in 381ba6c; the stale "allow these hosts" note in the still-judgment ledger was corrected in 61c642e. A frame-timing comparison in this GPU-less container found the final build within noise of the original page (both 2–4 fps headless with software rendering), so the UI work added no material rendering cost; smoothness on real devices, and Safari and Firefox, are untested here.

Tests at 381ba6c: `node tests/model.test.js` 7,468 pass; `node tests/browser.inputs.js` and `node tests/browser.sweep.js` pass. `node tests/fuzz.test.js 1500` last passed at 77c65b3 (173,364 checks); no model code has changed since.

## The owner's requests after the UI work, October 2026

The owner sent four requests, with screenshots of the probe and the status row:
- "make the two tabs look visually different. colors are enough but maybe some other stuff too"
- "if i scroll quickly, the scroll indicator on the left side should always keep up smoothly- it should not lag behind or teleport"
- "make the opening animation absolutely brilliant and stunning- it should be an entire universe animation and last 10+ seconds. (although just keep the current animation when travelling between tabs)"
- "remove this block of text entirely" (the masthead status row)

No number, model equation or existing sentence changed. The model source the tests load is byte-for-byte the same as at a884f41.

### The masthead status row (712e4b7)
The row under the masthead is removed, together with every rule that styled it, in eleven places in the stylesheets, including the phone layouts from UI round 3. The row read "Value, risk, timing · Fitted", "Transactions fitted · 60,141" and "Closing odds · Market aggregate". The tab bar keeps a clear gap under the masthead's last line at 1440, 1100, 820, 390 and 360 px.

The R3-1 test pinned the row's labels and its typed total. It now checks that the row, the old "Close and timing" label and the typed total stay gone. The same total is still on the page, computed from the two fitted samples, in the Data tab's tally.

### The probe on the mission line (712e4b7)
- **Cause.** A scroll listener moved the probe with a transform on the main thread. Browsers scroll on the compositor thread, so in a fast scroll the page moved first and carried the probe with it. The probe was corrected only on the next main-thread frame, and after a busy frame it jumped back.
- **Fix.** The probe is now `position:sticky` (top 42vh) inside a rail as tall as the column. The compositor holds it at the reading position in the same frame as the scroll, and there is no scroll listener.
- **Checks.**
  - At 41 scroll offsets from top to bottom, the sticky probe sits where the old formula placed it, including the bottom clamp. The largest difference is 0.00 px.
  - With the main thread blocked for 2.5 s during a wheel scroll, the old probe was carried 300 px off its line and then snapped back. The new one stayed at the reading position in all 56 compositor frames.

### Two tabs, two places (611419f)
- **Console.** Unchanged. With the animated canvases hidden it is pixel-identical at 1440, 390 and 360 px, both on first load and after a round trip to the Data tab. The computed styles of 11,389 elements and pseudo-elements are unchanged.
- **Data & parameters becomes the observatory.**
  - **Sky:** a deep blue-teal sky with a cyan-teal nebula, and a faint RA/Dec graticule that turns slowly. It is drawn in the existing sky shader, with no new loop. The drawn sky layers are seen through a cold filter.
  - **Masthead and tab bar:** an ice-cyan accent on the title's last word, a cold monochrome orrery and a cyan limb under the tabs. The tab bar is teal with a cyan active pill.
  - **Panels and section heads:** blue-teal glass panels with corner registration marks like a photographic star plate. The section heads get reticles round their planets, graduated rules and squared catalogue labels.
  - **Other details:** a ruler scale replaces the dashed gutter line, equation plates sit on plotting paper, and the foot of the page has a cold dawn.
- **Provenance colours keep their meaning.** No new decoration uses green, amber or coral. No badge, dot, tally figure, tally bar, tier planet or tier rim is recoloured.
- **Switching.**
  - The tab handler sets `html[data-tab]` in the same step that swaps the views, at the flash of the tab warp; the warp itself is unchanged.
  - The sky shader eases between the two skies over about a second. Under reduced motion it draws the new sky once.
  - Quick back-and-forth clicks always land on the tab clicked last.

### The opening: an entire universe (babf090, 20a2e30)
A WebGL film plays over the loading screen on every load, then hands over to the existing jump into the console.

The film, in film time (which runs 6% faster than the wall clock):
- **Before time** (while the console boots): a breathing point of light that brightens with the loading progress. Only one small quad is drawn while the boot runs. The bang waits for three things: the boot to finish, 1.9 s from navigation, and 1.3 s of the point on screen.
- **Big Bang** (0–1.15 s):
  - The point swells into a brief, soft white-out, never a disc.
  - A thin, turbulent shell sweeps past the frame edges in about half a second. It is brightest at its rim and runs white-hot to gold to orange, with red leading blue by at most 3 device px.
  - Hot debris streaks outward and past the camera, cooling from blue-white to red.
- **First light** (1.15–2.85 s): three smooth layers of plasma drift outward at different rates, from crimson to white-gold. They resolve into a fine speckle like the cosmic microwave background, which fades as the universe turns transparent.
- **Cosmic web and first stars** (2.85–4.8 s): matter slides onto filaments and nodes in 3D. The nodes have halos, there is a faint azure-violet gas glow, and the first stars ignite with glints.
- **Galaxies** (4.8–6.6 s): spirals and ellipticals form and turn, nebulae bloom, and the camera flies past two galaxies.
- **Home** (6.6–8.45 s): a dive into one spiral and through an arm to the Milky Way band. There, the Sun and five planets on thin orbits echo the masthead's solar system.
- **Title** (8.3–9.45 s): "The Omni Method" resolves under the Sun.
- **Frontier** (9.45–13.7 s, added in 9f94354): the finale described below.
- **Jump:** the unchanged hyperspace jump. Reveal and arrival run 1.85 s in, as before, onto the masthead's solar system. With a quick boot the console is revealed about 16.7 s after navigation (12.7 s before the finale was added).

Captions mark the time:
- "13.8 billion years ago"
- "380,000 years · first light"
- "200 million years · the first stars"
- "1 billion years · galaxies"
- "9.2 billion years · the Sun"
- "13.8 billion years · today"

They are hidden from screen readers. The loading steps are still announced.

How it is built:
- **Rendering.** Every frame is a pure function of time, so a dropped frame skips ahead instead of slowing the film. Particles carry seeds and are moved in the vertex shader by a time uniform, so no per-particle work runs on the CPU after setup. The plasma, nebulae, galactic disc and Milky Way are an fbm pass into a half-resolution buffer, compiled as two programs (bang and first light; galaxies and home) so that neither pays for the other's branches. Composite, point sprites, spark lines, orbit points and quads for the Sun and planets follow.
- **Load.** Stars scale with the viewport: 88,128 at 1440×900, 96,000 at 1920×1080 and 30,000 on phones. Resolution is capped at a pixel ratio of 1.5 and about 4.2 M device pixels. If the median frame exceeds 26 ms, quality steps down twice: to 60% of the particles, then to pixel ratio 1 with a smaller field.
- **The app behind it.** The boot steps run unchanged behind the first phase. The page's own sky (the v3 loop driver and the render code's WebGL sky) stands still while the film covers it, and resumes at the jump. At the end the film releases its GPU context, buffers and programs.
- **Skip.** A "Skip intro" button, Esc, Enter, Space or a click. A skip before the boot ends waits for it, then fades out in 0.4 s. Reveal and arrival run exactly once on every path.
- **Fallbacks.**
  - Without WebGL, after a shader failure, or on a lost GPU context, the previous drift and jump run.
  - Under reduced motion, a plain fade.
  - The tab-switch, reset and industry-change warps are untouched.
- **First paint.** A mark set before the loading screen first paints keeps the old title, bar and drift hidden until the film takes over, so a load opens on the dark void. The film removes the mark wherever it stands aside. Where a browser offers the WebGL API but refuses a context, the old loader therefore appears about half a second later than before.
- **Checks.**
  - Frozen frames at 1440×900 and 390×844, every 0.5 s through the film, every 0.15 s through the bang and first light, and every 0.03 s through the bang.
  - Real-time runs with WebGL2, WebGL1, no WebGL, reduced motion, skip (early, mid-film and during the jump) and a lost context (early and mid-film). All had no errors, one reveal and one arrival.
  - 16 shaders compile and 8 programs link with empty logs.
  - A screencast from navigation shows no loader flash.
  - The frozen-frame hook is `window.OMNI_INTRO.at(t)` or `?introAt=t`.
- **Not measured here.** This container has no GPU: WebGL runs on a software renderer at 2–4 fps (140–370 ms per frame at full quality). So the frame rate on real hardware, and the behaviour in Safari and Firefox, are untested. The adaptive steps above are the safeguard.

### The finale: the new frontier of brokerage (9f94354)
The owner asked: "After the universe animation, display something about how this is the new frontier of brokerage and some more crazy visual effects". A scene of about 4 s now sits between the title and the jump. Every frame before it is unchanged: frozen frames from 0 to 10.5 s match the previous version pixel for pixel.

The scene, in wall time on a quick boot:
- **Pull-away** (10.8–11.6 s): the solar system shrinks to a point, streaking inward. Speed lines run in, and a shockwave rings out with a faint red/blue split at its front.
- **Gate** (11.3–11.9 s): where the Sun was, a razor-thin ring ignites around a turning vortex in violet, azure and pink with a white-hot core. Electric arcs crawl along the rim, and stars bend into small arcs around it. The title lifts and shrinks into a letter-spaced "The Omni Method" eyebrow.
- **Particle headline** (11.7–13.1 s): thousands of particles pour out of the vortex and settle onto the letters of "The new frontier of brokerage". Their targets are sampled from the headline's real line boxes, so they land on the HTML text, including the two-line wrap on phones. The crisp headline then fades in, in the masthead's starlight-to-violet display type, and the particles shimmer out.
- **Ignition** (13.2–13.9 s): a light sweep crosses the words with an anamorphic flare riding it. Sparks burst from the letter edges, followed by a brief chromatic shimmer.
- **Collapse** (14.3–14.8 s): the headline and eyebrow are drawn into the gate as it flares, and the unchanged jump takes over.

Details:
- **Copy.** The eyebrow and the headline are the only new text, and both are hidden from screen readers, like the captions. The headline holds fully legible for 1.2 s.
- **Reduced motion.** The plain loader now shows the eyebrow and headline, still. Without WebGL the previous drift and jump run, without the headline.
- **Load.** Text particles and sparks number 8,652 + 1,038 at 1440×900, 10,944 + 1,313 at 1920×1080 and 4,360 + 523 at 390×844. The scene's GL work runs in its own programs, so the earlier phases cost what they did.
- **Cost here.** In this container's software renderer the scene costs about what the title does: 212–335 ms against 249–304 ms per frame at 1440.
- **Checks.**
  - Real-time runs with WebGL2, WebGL1, no WebGL, reduced motion, and skips early, during the scene and during the jump; also a context lost during the scene. All had no errors, one reveal and one arrival.
  - 24 shaders compile and 12 programs link with empty logs.
  - Alignment overlays confirm the particles land on the text at 1440 and 390.

### Tests
At 9f94354: `node tests/model.test.js` 7,468 pass; `node tests/browser.inputs.js` (15 checks) and `node tests/browser.sweep.js` (118 input states at 1440 and 390 px, no horizontal overflow, no NaN) pass. `node tests/fuzz.test.js 1500` passed at 49f3969 (173,364 checks), and the model source is unchanged since. One test changed: R3-1, as above. The browser tests now wait about 17 s longer per page load while the film plays; their 90 s boot timeout is unchanged.

## Stress test with invariants, October 2026

The owner asked: "Go back and stress test the model with stress invariants. Have agents make assertions and test if they're true in the app. Make sure everything is logical."

### How it ran
- **Four lenses.** Four independent stress testers each wrote their own invariants, about 250 in all, and ran them against a frozen copy of the build (380a52f). Each invariant states where its expectation comes from: a code comment, a MODELS note, the Data tab, AUDIT.md, or economics. Together they go beyond the roughly 100 the fuzz suite already asserts.
  - **Comparative statics (57).** Which way every input moves every headline output: value, price, closing odds, time to close, expected proceeds, survival risk, the scores, the proceeds-optimal ask, the optimiser, and the intervention and sensitivity rows.
  - **Identities, bounds and units (60).** Shares that must sum, reported gains that must equal recomputed ones, sensitivity rows against the finite differences they describe, helper functions against their comments, money formatting, and the Data-tab tallies.
  - **Extreme inputs (60).** The corners of the input space and beyond the sliders, fine scans across every cap and threshold, determinism, and how the exact-value boxes parse typed text.
  - **The live page (76).** At least 25 stress states entered through the real controls. Every figure and every directional word is checked against the model, along with reset and tab switching.
- **Verification.** For each lens with violations, one verifier reproduced every violation and then tried to refute it.
- **Result.**
  - **Every comparative-statics invariant held: no input moves any headline output the wrong way.**
  - Twelve violations were raised in the other three lenses. Five were confirmed, all low severity, and fixed (S-1 to S-5 in AUDIT_FINDINGS.md). Seven were refuted.

### What changed
- **S-1, the score's reference population.**
  - **Before:** where a peer median sits near a field's bound, the reference profiles were clamped off their stated quality composite. That lifted the bottom of the population, so weak small businesses scored 1-4 points low.
  - **After:** each clamped draw is solved for the scale that restores its composite exactly, read through a new qualityZ() that equals the model's own composite. A restaurant at the 10.2nd quality percentile now scores 10, not 9.
- **S-2, the GM salary.**
  - **Before:** three Census tables (car wash, auto repair, fitness) list size classes whose receipts per firm fall out of order. The GM salary jumped up to 4.1% on a $1 change in revenue, which could flip both optimiser recommendations.
  - **After:** out-of-order classes are pooled before interpolating. The salary is continuous and never falls with revenue.
- **S-3, the score cache.** The reference population was cached on six significant digits of size, so identical inputs could score 50 or 51 depending on the order they were entered. It is now keyed on the exact size.
- **S-4, the exact-value boxes.**
  - **Before:** whole thousands misstated small values, by up to a third under $10k ($1,499 showed as "$1k").
  - **After:** the boxes, the value table's "SDE × multiple" row, eq_vs, and the optimiser's money echoes (the intervention table's costs, both cards, the overall-outcome card's note, eq_rs, eq_os and eq_us) show three significant figures in thousands, as millions already did. Every box re-reads within 0.5% of the value the model uses.
- **S-5, the "Do nothing" card.** It said "no combination clears its cost" when changes that do were only over the budget. It now says that nothing within the budget clears its cost, and names the cheapest over-budget change that would. The old wording remains only where the budget covers every change.
- **Refuted, and left as they are.**
  - The $25k SBA 7(a) floor is documented and calibrated, and binds only below about $29k of value.
  - Signed zeros such as "−0%" are the sign-preserving rounding of tiny values. Red against green marks which side of break-even a row sits on.
  - A typed fractional buyer count is kept by design. The model is continuous in the pool.
  - The Bear scenario card collapses a sub-0.5% range to "the ask ceiling" by a documented rule.
- **No other change.** Nothing else moved: every other test, pinned figure and invariant is unchanged.

### Tests
- **The suite.** The invariants are kept in tests/invariants/ and run by `node tests/invariants.test.js`:
  - statics.js, identities.js and extremes.js hold the model parts, 154 invariants in about 3.5 minutes;
  - `--browser` adds their in-page checks and app.js, the live page, for 253 in all.
- **Assertions rewritten from the stress testers' copies.** Some assertions tested a pre-fix path or encoded the old formats, and some asserted behaviour the verification kept. They were rewritten to test what the page now reads, or to state the documented convention:
  - the Census tables as pooled;
  - the reference draws read from refDistAt;
  - the head count growing over every tenfold step of revenue;
  - the SBA loan rule with its floor, and the risk tile naming only the $5M cap;
  - a zero carrying the true sign of its change;
  - typed buyer counts kept as typed;
  - the Bear card's documented collapse;
  - the boxes and the optimiser's money echoes at moneyIn's precision;
  - the new "Do nothing" wording.
- **Regression tests.** model.test.js section 37 adds a test for each of S-1 to S-5; R4-6 now pins the budget box and the cards' budget echo to moneyIn.
- **Results at 62afc61** (index.html unchanged since b92052b):

  | Suite | Result |
  |---|---|
  | `node tests/model.test.js` | 7,473 pass |
  | `node tests/fuzz.test.js 1500` | 173,364 checks pass |
  | `node tests/browser.inputs.js` | 15 checks pass |
  | `node tests/browser.sweep.js` | 118 input states at 1440 and 390 px pass |
  | `node tests/invariants.test.js --browser` | 253 invariants pass: statics 57, identities 60, extremes 60, app 76 |

## Second round: the remaining judgment parameters, October 2026

The owner asked: "Find datasets for any of the parameters that are currently not fitted. If you can find them, go ahead and train the model and implement them into the program."

### How it ran
- **Research.** Eight lanes searched for public data behind every number the Data tab's ledger still listed as judgment: the peer table's medians and spreads, the size references, the buyer factors, the SBA tail, the price mechanics, the intervention costs, the category weights and the confidence formula. Downloads were kept as untrusted data and read with `python3 -I`.
- **Fits.** Ten scripts, now in `fit/` with their rows in `fit/README.md`. Eight went through up to four rounds. After each round an adversarial reviewer re-ran the script, recomputed its numbers independently and listed blocking defects. The fixes were applied and verified again. In the last rounds those scripts reproduced their outputs byte for byte, and nothing blocking was left. `industry_tailwind_and_comps.py` passed its own 22 checks and reproduced, but no reviewer re-ran it until the review after integration (below). `peer_checks.py`, a display-only record of the research round's checks that nothing reads, was not reviewed.
- **Decisions on review.** Among the defects the reviews caught and the fits corrected:
  - a gross-margin definition that left out payroll costs;
  - a double count of paid leave in the employer-cost loading;
  - confidence gradients that partly came from a parse error;
  - a size gradient that mixed price level with accuracy;
  - a growth level whose standard error was too small to cover a conflicting source;
  - an SBA tail table that was not like-for-like with the pooled factor.

### What was fitted
| Was judgment | Now | Data | Tier |
|---|---|---|---|
| peer median gross margin, one number per industry (.24–.78), no definition | a curve in revenue on one stated definition per industry (the owner's pay is not a cost; the definition shows on the slider's label): 39–85% at $1M of revenue, falling with size in 13 of 15 industries; car washes keep 0.70 | IRS SOI Source Book 2004–13 and Statistics Canada 2024, bridged to the definition with BLS OEWS wage shares and payroll costs; KBCM 2021 and Ratchet+Wrench 2026 combined for software and auto; e-commerce from 300 Empire Flippers sales | aggregate (e-commerce fitted) |
| peer median growth 4–25% | 0–8.5% for 15 industries: the median small business (5.0%, Chase) + a size bridge (+1.7 pts, Census BTOS) + the industry's deviation × its measured persistence (0.48; manufacturing 0.12); software keeps 25% (its sources disagree by 5.8 SE) | JPMorganChase Institute, Census BTOS / AIES / QSS / MRTS, BLS QCEW, Fiserv | aggregate |
| retention, landscaping 0.74 and fitness 0.62 | 0.88 and 0.66 | Lawn & Landscape 2025–26 surveys; Health & Fitness Association 2025 | aggregate |
| owner-dependence and management-depth slopes in size, −0.30 / +0.28 | −0.15 / +0.17 (levels 0.62 / 0.42 stay judgment) | Fed SSBF 2003 microdata, replicated by SSBF 1998, NSSBF 1993, SBO 2007 and listing text | fitted |
| width of the size z-score 0.45 | 0.48 decades | 10,187 DealLedger listings | fitted |
| industry tailwind, a hand-set score (−0.25 to 0.65) | −1..1 around the all-industry average | BLS Employment Projections 2025–35, bridged to realised growth | aggregate |
| comparables depth, a hand-set score | n/(n+25) of the industry's BIZCOMPS cell, the value model's own weight | BIZCOMPS counts behind the value model | fitted |
| individual buyer's multiple factor 0.90 | 0.97, so the buyer-type-weighted price averages to the fitted value | IBBA buyer mix and the BIZCOMPS-fitted value | calibrated |
| SBA tail ×1.20 for every loan (SE 0.08) | ×1.21 (SE 0.06), ×1.08 under $150k to ×1.30 at $0.75–1.5M by the note's size; the average loan's 10-year base 5.64% → 5.73% | 152,121 SBA 7(a) loans approved FY2010–15, matched to the acquisition book | fitted |
| QoE fee max($22,000, 0.45% of revenue) | max($16,400, 0.19% of revenue) | 33 published fee tiers from 15 sources | aggregate |
| hire a GM: one year's wage; the wage off earnings | one year's wage × 1.24 + $10,625 to hire; the loaded wage off earnings | BLS ECEC June 2026; SHRM 2025 | aggregate |
| sales-hire floor $55,000 everywhere | $27,200–$81,500 by industry | BLS OEWS May 2025 sales-rep wages × ECI × ECEC, SHRM | aggregate |
| confidence index .34 comps + .30 years + .22 reporting + .14 typicality, cut at .68 / .46 | the chance the price lands within 25% of the fitted value; High / Moderate / Low = top quarter / middle half / bottom quarter of listed businesses; Low "outside the fitted data" past 3× or with the earnings margin outside its 1st–99th percentile | BIZCOMPS out-of-fold accuracy and fan; 2,710 DealLedger Main-Street asks; the value model's 6-digit effects | fitted (scale calibrated) |

**Checked and kept as judgment**, each with its evidence recorded in the table it would have come from:
- strategic interest and typical buyer pools (`peer_checks`: vendor trackers see institutional deals only);
- the search fund's window (`buyers.eta_check`: a measured curve fits IBBA worse and breaks the $2–5M pin);
- recurring-revenue medians (`peer_rec_ret.not_shipped`, `flags`);
- reporting's line and the peer spreads (`size_refs.checks`, `peer_rec_ret.spread_checks`);
- three other intervention costs (SOPs, contracts, outreach), four durations (QoE, GM, sales hire, SOPs) and the QoE effect (`interventions.checks`). The diversification, margin, retention and channel programmes have no benchmark. The price mechanics, the category weights and the other effects were searched too. Nothing found identifies them (old IBBA termination rates give only the direction of the $1M–$5M base-rate ramp), and no table records them.

### What it changes on the console
- **Peer comparisons.** A business entered at the old hand-set medians now sits off the fitted ones, so its quality position moves. At $300k of SDE the value moves −17% (e-commerce, whose margin is now measured on landed cost) to +3%; at $1.5M it moves −14% to +11%. A business at the new medians keeps the fitted value.
- **Confidence.** The framework example reads 0.54 (High), and was an index of 0.70. Businesses at their industry's typical margin read 0.47–0.58 at $300k–$1.5M of SDE. Years in business and reporting no longer move it.
- **Survival risk.** The 10-year figure is the fitted 8-year figure times the tail at the note's size. It falls about 0.5 pt at a $200k note and rises about 0.4 pt at $2M. The risk tile's badge now reads "fitted". The framework example reads 3.43%, and was 3.18%.
  - From a note of about $0.60M to the $1.05M band centre the tail rises faster than the 8-year figure falls. There, the 10-year figure can rise slightly with the note's size, and so with quality: at most 0.67% per 10% step, 3.6–3.8% across the range, by industry and state. The expected loss rises by at most 1.1% over the same range. The 5- and 8-year figures never rise.
  - The invariant suite found this. Its risk-in-size and risk-in-quality invariants now allow the 10-year figure to rise only where the tail rises, and by no more than the tail does. model.test.js already allowed 1% per step.
- **Interventions.**
  - The GM's cost and its charge on earnings rise by the 1.24 loading, and the cost adds the hire.
  - The QoE fee falls at every size; the floor binds up to $8.6M of revenue.
  - The sales hire's floor now differs by industry.
- **Typed figures that moved.**
  - The walk-away ask at $150k of SDE and $4,000 a day is 1.08×, and was 1.09×.
  - The weak restaurant in S-1 scores 7, and scored 10.
  - The framework example's Omni scores and time to close are unchanged.
- **Tallies.** The Data tab's headline moves from 537 fitted, 38 aggregate and 432 judgment to 565, 147 and 353. The counts are computed from the tables:
  - 80 numbers leave the judgment ledger and one enters, 79 net. Out: 64 peer-table cells, the QoE fee's floor and share, the $55,000 floor, the individual's multiple factor, Market position's .65 offset, the tailwind delta's .30 offset, six of the confidence formula's eight (its four weights and two scales; the two label cut-offs stay, re-set to quartiles), the two hand-set size slopes, the size z-score's width and the SBA tail factor. In: the confidence label's extrapolation rule (Low past 3× the fitted data);
  - 28 are counted as fitted: the size slopes and width, comparables depth, e-commerce's margin, the tail's five band ratios and the confidence gradients and depth;
  - 109 are counted as aggregate: the margin curves' 56 knots, 15 growth medians, 2 retention medians, 16 tailwinds and 20 intervention benchmarks;
  - the individual's multiple factor and the confidence scale are calibrated and counted in no tally.

### Review after integration
Three reviewers read the integrated round against the page before it: the model and every reader of the changed tables, the Data tab, and the docs, tests and fit scripts. A verifier then re-checked each finding from scratch. Every confirmed finding is fixed:
- **The judgment tally was one too high.** The ledger counts the typed numbers in the multiple stack from its source, and a comment that still named the removed tailwind offset (.30) was counted. Comments are now stripped before counting: 353, not 354.
- **The confidence formula as printed did not reproduce the figure for large or tiny businesses.**
  - It gave the window around V, but the figure is computed around the fitted value before the quality position (V/q).
  - It also left out that SDE is held inside the value model's support ($13k–$1.70M). For home services at $5M of SDE, the printed formula gave 0.60 against the 0.56 shown.
  - eq_c now prints V/q and SDE\*, with SDE\*'s definition on a key line under the formula, as eq_s's is, so the formula still fits mid-size cards. A test checks the printed σ against the computed one.
- **Small software businesses could not be entered at their own median.** The fitted software margin is 93% below $316k of revenue, above the gross-margin slider's 92% cap. The slider now runs to 97%, the field's own limit, and the invariant suites' slider ranges moved with it.
- **An unlisted industry had no margin median.** peerGm fell back to `IND.prof.gm`, which the round removed, so the quality composite came out NaN. No console path reached it. It now reads professional services' curve, as `peerMedians` does for the other medians.
- **`buyer_factors.py` failed on the current page.** The page says to re-run it when the buyer factors change, but its probe built test businesses from `IND`'s gross margins, which gave NaN. It now reads the page's curve where the page has one. On the page it was fitted on, its results are unchanged.
- **Page wording and labels:**
  - the general-manager cost is set by four series, not two;
  - the judgment lede notes that where data bound or dispute a hand-set number, the check is recorded;
  - the extrapolation rule names its margin test;
  - the tail row's top band is computed, as trap 4's is;
  - the gross-margin definition is stated per industry;
  - comparables depth is credited to BIZCOMPS, not public data;
  - the intervention checks are listed as three other costs, four durations and the QoE effect;
  - the GM's ECEC loading is labelled aggregate in the table and in `intervention_costs.py`;
  - the risk tile's title gives its product to two and three digits, without claiming equality;
  - the code comments that said the same things.
- **This file and `fit/README.md`:**
  - the "checked and kept" list claimed records no table holds;
  - the old tailwind's range;
  - where and by how much the 10-year figure can rise with the note;
  - what left the ledger;
  - which scripts were reviewed;
  - an earlier section's "none can be fitted";
  - 14 aggregate margin curves, not 15;
  - README row 12's tail, and what to re-apply after re-running `sba_risk_refresh.py`;
  - the buyers and peer-checks rows' inputs, and the EM's attribution;
  - the harness, now shipped as `fit/harness.js`;
  - a note that the earlier rounds' scripts are records whose anchors later rounds changed.
- **Tests:**
  - 38a's definitions check could not fail, and the margin curve between its knots was untested;
  - the fitted 80% band was untested;
  - the years invariants still listed confidence among what years may move. The browser check now also holds the confidence tile and eq_cs fixed when years change.

**The tailwind fit, reviewed after integration.** `industry_tailwind_and_comps.py` had shipped on its own checks, so a reviewer re-ran it and recomputed it independently from the raw BLS files:
- the bridge, 0.958 and 0.273 with sector-clustered SEs;
- the anchors, 3.062 and 1.107 pp/yr;
- all 16 tailwinds to four decimals;
- the SEs;
- the out-of-sample block;
- the comparables weights.

Every shipped number reproduces, and nothing blocking was found. Recorded, not changed:
- **Two job counts in one map.** The jobs map compares industry lines that count wage-and-salary jobs with the all-jobs rate, which includes the self-employed. Made consistent, every tailwind moves by 0.004–0.006, and seven of them change by 0.01 after rounding. That is well inside their SEs (0.07–0.33).
- **Restaurants map narrowly.** Restaurants read full-service restaurants only, following the value model's industry cell. All of food service (NAICS 722) would give +0.07 against −0.02, a gap larger than its SE of 0.08.
- **Construction maps narrowly.** Construction reads the residual line of other specialty trades. All specialty trades would give −0.10 against −0.03, inside its SE of 0.29.
- **The output map's zero.** It is the output-weighted mean of the bridge, so an industry growing exactly at the all-industry rate reads −0.02 on the tailwind.

### Tests
- **Section 38** of model.test.js covers each new table:
  - the gross-margin curve, its flat ends and every industry's definition;
  - the cells written into IND, and FITTED_CELLS;
  - sizeRefs and SIZE_SD;
  - the three costs against the published benchmarks;
  - the confidence fit's ten test vectors, its label rule and its directions;
  - a Data-tab row for every fit, with no stale wording.
- **The survival-risk tests** check the tail against an independent interpolation of the band table, re-pin pTerm, lgd, expLoss and rel (p5 and p8 are still the Python mirror's), and check the term base, its SE and its range.
- **The fuzz suite** gains the confidence identities. The invariant suite reads the fitted label rule, a confidence that does not move with reporting or years, the risk badge and the new eq_cs.
- **The invariant suite's own revisions:**
  - the two risk invariants above;
  - the Data-tab recount extended to the second-round tables;
  - the walk-away invariant's dollar check put on bestRatio's 2e-4 resolution. Its ratio check already used that resolution, but the dollar check used 1e-6, which failed by 3e-5 in two of 444 cases where value barely moved.
- **Results**, on the final build, after the review fixes:

  | Suite | Result |
  |---|---|
  | `node tests/model.test.js` | 7,512 pass |
  | `node tests/fuzz.test.js 1500` | 179,746 checks pass |
  | `node tests/browser.inputs.js` | 15 checks pass |
  | `node tests/browser.sweep.js` | 118 input states at 1440 and 390 px pass |
  | `node tests/invariants.test.js --browser` | 253 invariants pass: statics 57, identities 60, extremes 60, app 76 |

## Skeptic review and recurring motion, October 2026

The owner asked: "Now do the review loop to ensure everything is working as intended (have skeptics test everything), then just add recurring animations like everywhere (but make them tasteful)."

### The skeptic review
Four skeptics tested a frozen copy of the page at 53e6498. Each was told to break its area and to report only defects it could reproduce:
- **The model, in node.** Random and extreme inputs over every industry and state, the identities the page states, monotonicity, determinism, and five headline outputs recomputed from the tables.
- **The interface, in a browser.** Every slider by keyboard and drag, every typed box with valid input, suffixes and junk, the selects, reset, the optimizer, tab switching; inputs and outputs checked against a fresh model run, at 1440 and 390 px.
- **Every displayed figure.** Tiles, sub-lines, tooltips, tables, chart labels and every equation against the model output and the stated formulas, for seven very different businesses, and the Data tab's computed text against the tables.
- **Layout and robustness.** Seven widths from 320 to 1920 px and a short viewport, with and without motion, tab switching, resizing, text zoom, print emulation, focus visibility and page errors.

**The model.** The skeptic rebuilt the fitted value, closing odds, time curve, expected price and SBA charge-off from the tables with its own code. Over thousands of profiles they agreed to 1e-7 or better. Five hundred profiles at the bounds gave no non-finite output, and about thirty identities and monotonicity rules all held. It found three low-severity defects, each confirmed and fixed:
- **MODEL-1.** The walk-away note judges whether a second peak is real by the dip between the two peaks, but it read the dip off the 0.02 grid of ask ratios. For one veterinary profile the grid sat beside a kinked bottom. It measured $191 against the page's own rule of 0.01% of value ($288), where the true dip is $306, so the note said "there is no second peak" about a real one. The dip's bottom is now searched between the grid minimum's neighbours (14 golden-section steps), the same way the peak itself is refined.
- **MODEL-2.** A comment and the SOI wedge's `why` text said the SDE-to-EBITDA wedge falls monotonically from 1.90 at $100-250k of revenue to 1.08 above $100M. The table the page ships is 1.87 at $100-250k and 1.90 at $250-500k, then falls to 1.12 at $50-100M. Both texts now say that.
- **MODEL-3.** A comment gave the BIZCOMPS band's implied sigma as 0.472; it is 0.468, the figure the Data tab prints.

**Every displayed figure.** The skeptic recomputed every tile, sub-line, tooltip, table and equation for seven profiles, against the model and the stated formulas. Of its nine findings, eight were fixed in whole or in part:
- **D1 (medium).** The time-to-close equation printed `e^{0.10 h}` without defining h, while the value equation on the same tab defines h as the SDE hinge. Substituting that h gives a median about 25% longer than the one shown. The exponent is the ask's log gap over value, smoothed near zero. It is now called g, defined in the label and printed with its value.
- **D2.** The scenario sub-equation printed R at the 10th and 90th percentiles but P at the 8th and 94th. It now prints R at the same levels as P, from the fan's quantile function.
- **D3.** The Data tab's extrapolation table was typed in and had drifted from the console's warning: a 2.2% margin percentile against 2.3%, on a tab that says its tables are generated from the live constants. It is now generated from `MODELS.value.support` in the warning's own formats, and so are the two figures in the paragraph above it.
- **D4 (refuted).** The business-score caption's "optimal ask of $4.63M and a typical 59 buyers" sits beside "the optimal ask of $4.62M" for a five-buyer pool. The first caption names its pool, so these are two different, labelled optima.
- **D5.** The price tile's tooltip said the prices are capped at the ask. Above about $9M of value, IBBA's size band closes above the ask, and the tile shows that. The tooltip now names the ask ceiling.
- **D6.** The sensitivity note used singular grammar for several one-sided rows. Fixed.
- **D7 (in part).** The signed zeros it found ("−0.0%", "ROI −0%") follow the page's convention, pinned by the invariant suite: a change keeps its sign when it rounds to zero. That part is refuted. The quality band's ASCII hyphen-minus is now U+2212, as on every other figure.
- **D8.** With the ask under value and binding, "Repricing is the lever" quoted only a 5% cut, which loses money. It now gives the 5% raise first, then the cut that the sensitivity bar shows.
- **D9.** With no cost of delay, the optimizer note still said a higher ask lengthens the time to close, "which only the second figure charges for". That clause now appears only when delay has a cost.

**Layout and robustness.** The skeptic tested seven widths from 320 to 1920 px, a short viewport, 200% zoom, resizing, the full film, keyboard focus and print. Away from 320 px and print, it found no overflow, clipping, overlap, KaTeX error or page error. It reported five findings, all confirmed:
- **VIS-1 (medium).** At 320 px the buyer star map could drop the label of the buyer to pursue first, because no candidate box fit inside the plot. In another state it overprinted two labels. A label with no room in the plot is now clamped inside with a leader line, and on a phone the plot may grow four times instead of two. The model-value label may also sit a little off its line. The skeptic's states now draw 8 of 8 labels with no overlap at 320, 360, 375 and 414 px.
- **VIS-2 (medium).** Printing with Chrome's defaults made the title, both scores and the headline figures invisible: they are gradient text, and print drops backgrounds. A print style now gives them solid ink and leaves out the fixed backdrop layers. **Still open:** in Chrome's PDF output the hero caption and the quality note lose their right half. Print emulation shows no ancestor clipping them, and the cause was not found in the time available.
- **VIS-3 (low).** At 320 px the time curve's median label could print over the 365-day callout. It now tries six more spots, and if none is clear it takes the one that overlaps least.
- **VIS-4 (low).** At 320 px the chance-of-closing tile cut its "aggregate × judgment" badge mid-word. Below 360 px the badge now wraps.
- **VIS-5 (low).** On phones the closed rail dropdowns cut their option mid-word. They now end with an ellipsis; shorter option labels were not attempted.

**The interface.** The skeptic ran every slider by keyboard (126 actions) and by drag, 331 typed cases in 14 boxes, every industry, state and option, reset, the tabs, 14 optimizer budgets and 150 random profiles. Each time it checked the state, the boxes, the sliders and the tiles against a fresh model run, with 0 mismatches. It reported two low-severity findings; one was confirmed and fixed, and the other was refuted:
- **ui-1.** At phone width, money ticks of six characters on the star map lost their "$": "$12.5M" read "12.5M" in a 40 px gutter. The gutter now grows to fit the widest tick.
- **ui-2 (refuted).** The buyers box keeps a typed fraction, so the captions can read "12.5 buyers". The stress test kept this by design, because the model treats the pool as continuous (an expected-offer count), and the invariant `buyer-count-kept-as-typed` pins it. A rounding fix was tried and reverted when that invariant failed.

**A second figures skeptic.** The review workflow also ran its own display lane, independently of the first. Two of its findings repeated D3 and D9; the other four were new, and all were confirmed:
- **DISP-1 (medium).** The buyer table's "Synergy captured" column printed each buyer's whole synergy S, 2.6 times the seller's share that its price holds. It now prints that share (0.38 × S), as the header and the section lede say.
- **DISP-2 (low).** The sensitivity note called a lever "already at the end of its range" whenever a bound clipped one of its steps, for example customer concentration at 5% against a 1% floor. It now says "at or near the end" and calls the row an uneven difference.
- **DISP-3 (low).** The overall-outcome equation printed P_C to the whole percent, and the competition equation printed offers to one decimal, too coarse to reproduce their results: $50.28M against $50.21M, and −1.2% against −1.3%. They now print 0.1% and two decimals.
- **DISP-5 (low).** The value gap "if every value-adding change is made" silently left out the changes the bundle prunes. For example, a GM hire adds $134k on its own and nothing once the other changes are made. The note below the gap now names them.

The workflow's verifiers did not run: the lanes ran past the time box, and the workflow was stopped before its second layout lane reported. Instead, each finding was reproduced against the code before it was fixed. Two whole findings (D4 and ui-2) and two of D7's three parts were refuted.

### Recurring motion
A motion layer (`v10-motion`) adds slow, low-contrast loops wherever the page was still once loaded:
- **Section labels.** A soft light crosses each framework pill in turn, under the text, and the pills' glyph dots breathe; on the Data tab the emblem's three provenance dots take turns.
- **Equation cards.** A hairline of light runs along the top edge, a few seconds apart from card to card.
- **Bar charts.** A glint travels along each bar, row after row: the quality z-scores, the closing contributions and the other bar charts.
- **The hero.** The quality marker sends out a slow sonar ring, and the two score dials' glow discs breathe out of step.
- **The rail.** Each group rule carries a passing light.
- **The tab bar.** The active indicator breathes.
- **The Data tab's tally.** The four orbs breathe in turn, and a light runs along the fitted, aggregate and judgment spectrum.
- **Key figures.** When a headline figure changes, it glows for under a second, only if it is on screen. Dragging a slider restarts the glow instead of stacking more.

How it stays tasteful and safe:
- **What moves.** Every loop moves only opacity, a transform or a background strip a few pixels tall. None changes text, size or layout, and the sweep found no horizontal overflow at 1440 or 390 px.
- **When it runs.** A loop runs only while its block is on screen: an observer sets `.m-on` on each section, the hero, the rail and the tally, and clears it when they scroll away. The tab indicator, always in view, is the exception. Nothing starts until the opening film has gone.
- **The glow.** It is a Web Animation, so no class, style or attribute of a figure is written; the invariant suite's snapshots of the tiles are untouched.
- **Reduced motion.** The page's global rule stops every loop, and the script skips the glow.
- **Cost.** Long tasks and frame rate in idle headless Chromium matched the page without the layer, which is dominated by the existing canvases.
- **Tests.** Section 39 of model.test.js pins these rules: what the keyframes may move, which loops are gated, and what the script may write.

### Results
- **Tests.** Section 40 of model.test.js pins each fix: MODEL-1 on the skeptic's own profile, and the rest by the code that makes them. Before these fixes all six of its checks fail, and section 39 fails without the motion layer.
- **The skeptics' own scripts, rerun on the final build:**
  - The star map draws 8 of 8 labels with no overlap in the four named states at 320, 360, 375 and 414 px, and the median label clears the 365-day callout.
  - "$12.5M" keeps its "$" with 7 px to spare.
  - The extrapolation table matches the console's warning.
- **The motion layer on the final build.** Run with full motion, blocks switch on as they scroll into view, the loops run, figures glow when a value changes, and there are no page errors.
- **Suites,** on the final build:

  | Suite | Result |
  |---|---|
  | `node tests/model.test.js` | 7,522 pass (7,512 before; sections 39 and 40 are new) |
  | `node tests/fuzz.test.js 1500` | 179,746 checks pass |
  | `node tests/invariants.test.js --browser` | 253 invariants pass: statics 57, identities 60, extremes 60, app 76 (see the note below) |
  | `node tests/browser.inputs.js` | 15 checks pass (see the note below) |
  | `node tests/browser.sweep.js` | 118 input states at 1440 and 390 px pass, with full motion on |

  The random chart sweep the layout skeptic wrote (50 states at 320 and 390 px) found 2 star-map overlaps before the fixes and none after. The inputs suite's first run on the final build was made while two other browser jobs loaded the machine. It missed the 1.5 s window for a quick Data-then-Console switch. A rerun passed. Eight timed switches each, on the page before and after these changes, landed within 3-700 ms on both, so the motion layer did not cause the miss.

  The first full invariants run on the final build failed one invariant, `buyer-count-kept-as-typed`, which showed that ui-2 was intended behaviour. After the revert, extremes.js was rerun and all 60 of its invariants pass.

## Third round: data for the remaining judgment numbers, October 2026

The owner asked: "now, see if there are any other datasets you can use to fit more parameters, and update all models and the code accordingly." In the same session they also asked: "in the opening animation during the solar system the camera goes to the left then back to the right for some reaosn. fix that. dont have it shake like that".

### How it ran
- **Research.** Four lanes searched for data behind every live judgment number, each with a different target:
  - retention and recurring revenue;
  - buyers and the price mechanics;
  - the peer spreads, medians and size references;
  - the interventions, the category formulas and the confidence label.

  Each lane was followed by an adversarial verifier. The verifier re-read every figure from the downloaded files, recomputed every estimate with its own code, and gave a verdict per finding.
- **Sources.** Only public copies were used: publishers' pages, government statistical agencies, a state franchise registry and the Internet Archive. No logins, paywalls or bot challenges were bypassed. For example, digitalcommons.pepperdine.edu sits behind a bot challenge, so the Pepperdine reports were read from the Internet Archive's copies, whose digests are recorded. Downloads were treated as untrusted data: they were read with `python3 -I`, and nothing downloaded was executed.
- **Approach.** The lead from the second round was definitions. Many benchmarks had been left unshipped because the console never said what its sliders measure.
- **Fits.** Two scripts are in `fit/` with their transcriptions in `fit/data_round3/` and their rows in `fit/README.md`:
  - `round3_gap_axis.py`;
  - `round3_peer.py`, which stops without writing if any of its 89 quoted figures differs from its local file.

  Both reproduce their outputs byte for byte.

### What was fitted
| Was judgment | Now | Data | Tier |
|---|---|---|---|
| Pepperdine's valuation-gap buckets read as 10–50% over model value, the open >50% bucket at 100% | the gap as Pepperdine defines it, a share of the seller's asking price: the edges sit at 11.1, 25, 42.9, 66.7 and 100% over value (p/(1−p)); the open bucket at 200% (judgment) | Pepperdine Private Capital Markets reports 2017–2026, investment-bank survey (the definition is printed in the 2025 and 2026 reports; ten vintages pool within 0.013 of the shipped shares, which are kept) | aggregate |
| customer retention, no stated definition | by customer count: of last year's customers, the share who bought again; stated on the slider, which now starts at 5% | — | definition |
| retention: e-commerce 0.40, auto repair 0.58, restaurants 0.45 | 0.25 (SE 0.05), 0.45 (0.05), 0.27 (0.10) | Little Stream's Shopify study and Bluecore 2025; Auto Apps shop data; Bloom Intelligence 2025 (the middle of the range its figures support) | aggregate |
| the MSPs' recurring share 0.72 | 0.42 (SE 0.066) | ScalePad 2025 and 2026, Datto 2019 | aggregate |
| car-wash gross margin 0.70 | 0.80, flat (SE 0.054 at the sites' revenue, up to 0.14 at the curve's ends) | Tommy's Express franchise disclosures, Item 19 (536 site-years; 0.835 measured on the definition, shaded for formats) | aggregate |
| the largest customer's median 0.16 everywhere | 0.14; manufacturing 0.19 (SE 0.02) | Value Builder's owner survey; Statistics Canada's Survey of Innovation | aggregate |
| peer spreads of growth and the largest customer's share, 0.13 each | 0.16 (SE 0.027) and 0.18 (SE 0.02), the scales at which each clamped z-score has unit variance on its slider's range | Statistics Canada's Canadian Survey on Business Conditions 2023–25; Value Builder | aggregate |

**Checked and kept**, each with its evidence recorded:
- **Recorded on the page** (`peer_rec_ret.not_shipped`, `flags`, `definitions.rec_check`, `peer_sd.checks`):
  - nine other retention medians;
  - whether "recurring" means subscriptions only or anything under contract (the label is unchanged; the readings that would separate them are recorded);
  - the other seven peer spreads;
  - the owner-dependence and management-depth levels and reporting's line.
- **Checked by the buyers-and-mechanics lane, recorded here:**
  - **RHO_MAX.** It is a judgment cap. Any cap above 1.5 leaves the patient seller at the cap, and its texts no longer call it the edge of the data.
  - **PEN_MAX.** An analog from Pepperdine's withdrawal ratios spans 0.15–0.59, so it does not identify the scale.
  - **The $1M–$5M base-rate ramp.** Pepperdine's resolved close rates by band (0.57–0.66) give its direction only.
  - **The strategic premium.** It trends down by 0.7 pt a year, and the shipped factors sit between the pooled and recent readings.
  - **PHI, the search-fund window, the competition bounds and IND.buyers.** No number moves.
  - **The MBO window's lower edge.** A new-ESOP size distribution (DOL Form 5500) gives about $1M as an industry-median reading of a proxy, not a fit.
- **Checked by the interventions lane:** no intervention cost, duration or effect moves.
  - The outreach cost's bridge from data-room fees does not measure the console's quantity.
  - The SOPs floor's sources price small-scope packs.
  - The growth share, the diversification floor, the channel, retention and contract costs, the durations, the effects and the confidence label's cut-offs all reproduce as checks.

### What it changes on the console
- **The price-gap penalty arrives later.**
  - An ask of 1.3× value keeps 75% of the base closing rate, against 64% before; 1.5× keeps 62%, against 58%.
  - The framework example's walk-away ask (75% kept, $900 a day) moves from 1.15× to 1.26×. At $150k, $400k, $1.45M and $5M of SDE it is 1.17×, 1.19×, 1.26× and 1.20×, against 1.13–1.15× before.
  - The knife edge at which the cap wins moves to 78% kept at $900 a day, 77% with no delay cost and 83% at $4,000.
  - The tail past the last knot decays from 200% over value, at half the old rate (k 0.000571).
- **RHO_MAX's wording.** The cap stays 1.5× as a judgment. Its texts no longer call it "the highest ask the closing data resolve", because Pepperdine resolves gaps up to half the ask, 2× value.
- **The walk-away note.** It now offers a range only for a real second peak: one with a dip of 0.01% of value, or one where the walk-away ask sits one 1% step of the share kept away. On the stated axis the framework example showed a 0.002% wiggle at 1.21×, which offered a range of 1.20–1.26× and hid the cap, 0.38% of value away. (The same range came back through the jump rule below: one step of the share kept away the walk-away ask is 1.20×, so that peak is real, and the note named only the best of the near-tie peaks. It still hid the cap until the sixth skeptic round of the broker tools; the range now spans every real peak within 1% of value, 1.20–1.50× here.)
  - The fuzz suite found that the dip rule alone was too strict. An MSP's walk-away ask jumped from 1.34× to 1.45× between 98% and 99% kept, over a dip under 0.01% of value, and at 98% the note showed no range. A peak the ask jumps to now counts as real however shallow its dip, and a test pins the case.
- **The peer table.**
  - **At the medians.** A business entered at its industry's medians keeps its value exactly.
  - **At the old medians.** One entered at the old hand-set medians moves:
    - −0.9% in most industries, because 0.16 now sits above the largest-customer median;
    - +6.7% to +9.6% where retention or the recurring share was set above the measured median (e-commerce, auto repair, restaurants, MSPs);
    - −7.1% for car washes, whose 0.70 margin is now below the median;
    - +1.2% in manufacturing.
  - **The framework example.** Its value falls 0.9% ($4.09M to $4.05M). Its Omni score moves from 41 to 40, and its business score from 79 to 77. Its closing probability (68%) and its walk-away ask as a multiple of value (1.26×) are unchanged.
  - **The weak restaurant (S-1)** scores 16 (7 before): its 45% retention now sits above its peers' 27%.
- **Tallies.** The Data tab's aggregate count rises from 147 to 156, and judgment falls from 353 to 345. Both are computed from the tables:
  - five IND cells leave the ledger: three retention cells, the MSPs' recurring share and the car-wash margin;
  - so do two of PEER_SD's spreads and the largest-customer median;
  - the flat car-wash margin curve counts as one number.

### The opening film
The camera's path ran Catmull-Rom tangents through its keyframes. Where a channel comes to rest these overshoot. As the camera reached the Sun its target carried on past it and came back: between film time 8.3 and 9.5 the Sun swung from 15% of the half-width left of centre to 13% right and back.

The tangents are now monotone (PCHIP), so no channel overshoots a keyframe. During the dive, the target's progress toward the Sun follows the camera's distance, so the Sun's offset from the centre only shrinks (ab69492). Section 41 of model.test.js evaluates the path outside the browser. On the old page it finds 3,360 overshoots, and the Sun 0.22 of the half-width off centre after arrival.

### Tests
- **Section 42** of model.test.js covers the round:
  - **Gap axis:** the knots from the stated edges, the penalty's continuity through the open knot, and the shares kept at 1.3× and 1.5× on both axes.
  - **Peer table:** every new cell and its table, the restaurant rule, the slider's new range and its definition, car washes' per-knot SEs, the concentration median by industry, the two spreads and the sensitivity steps that read them.
  - **Data tab:** a row for every fit, and no process notes in the embedded tables.
- **Section 40's MODEL-1 pin** runs on a build with the old axis and the old peer comparison. The stated axis removed the skeptic's second peak, and without the golden-section search that build's note again says "no second peak". The live note is checked against a fine grid.
- **Other re-pins.**
  - The walk-away asks, the knife edges, the flip scenarios and the 28a margins.
  - The median-business score pins (half pool 1–23, three quarters 16–41). The stored integration record is kept, as the Data tab says.
  - The ledger counts.
- **The invariant suites.** They read the live knots and the new retention range, and recount the new tables.

- **Suites,** on the final build:

  | Suite | Result |
  |---|---|
  | `node tests/model.test.js` | 7,549 pass (7,526 before; section 42 is new) |
  | `node tests/fuzz.test.js 1500` | 179,746 checks pass |
  | `node tests/invariants.test.js --browser` | 253 invariants pass: statics 57, identities 60, extremes 60, app 76 |
  | `node tests/browser.inputs.js` | 15 checks pass |
  | `node tests/browser.sweep.js` | 118 input states at 1440 and 390 px pass |

  The gap-axis commit passed all 253 invariants on its own build.

  The first full invariant run on the final build failed one check, `reset-restores-defaults`. It pinned the framework example's value at $4.09M, and the peer fits move it to $4.05M, as recorded above. The pin was updated, an identities state that typed the old value as its ask was moved to the new one, and both parts were rerun: all pass.

## Broker tools, October 2026

Asked what in the console would help a working business broker, I named four tools it could add on top of the models. The owner asked: "build all four of those." They are:
- an add-back worksheet that builds SDE from tax returns or income statements;
- a debt-coverage check at the asking price, on SBA's rules for financing a business purchase;
- a one-page seller report to print, save as PDF or download;
- saved deals, which compare a broker's own listings and sales with the model, and which can in time fit two of the judgment numbers.

None of them changes a figure the model reports. They read the model, and the Data tab's tallies (565 fitted, 156 aggregate, 345 judgment) are unchanged.

This section describes the tools as they now stand. "Skeptic review of the broker tools" below records what that review found and changed.

### How it is built
- **Pure functions in the model half of the script,** before the test loader's cut, so the tests run them without a browser:
  - `debtCheck`, `maxFinanced`, `noPriceWC` and `covFmt`, with `annualPayment`, `sbaRateLoan`, `marketPay` and the rounding helpers `moneyDown` and `moneyUp`;
  - `recastSDE`, `recastNotes` and `recastWeighting`;
  - `dealPredict`, `dealsStats`, `fitPenaltyScale`, `olsFit`, `sampleSummary` and `t95`;
  - `reportData`, `reportLevers` and `reportHTML`, with the paper's stylesheet `RP_CSS`, its page size `RP_PAGE`, the page's copy of the sheet (`rpScope`) and the downloaded file (`reportFileHTML`).
- **The page code** comes at the end of the main script. It adds:
  - a toolbar above the hero;
  - a "Financing check" section after the budget optimizer;
  - a link under the earnings input in the rail;
  - a third tab, Deals;
  - the worksheet and the report, as dialogs.
- **Rendering.** It hooks `window.render` the way the later scripts do. The financing table and the toolbar follow every render.
- **Inputs that skip the full render.** Inputs inside `[data-norender]` (the financing check, the Deals tab and the dialogs) redraw only their own part. A keystroke there no longer re-runs the whole console and its 2,048-call optimizer: the browser test counts zero renders.
- **Storage.** Deals and preferences stay in this browser, under `localStorage` keys `omni.deals.v1` and `omni.prefs.v1`:
  - everything read back is cleaned first, imports included, because both are untrusted;
  - when storage is refused (a private window), every save says so and the Deals tab says the deals last only until the page closes; a full store is named as full;
  - another tab of the page writes the same store, so every save first merges with it: the newer copy of a deal wins, and an edit's time is always after the copy it was made from, whatever the clock. A deletion is kept with its time (`omni.deals.v1.deleted`, merged before it is written) so an older tab cannot bring the deal back, and a backup that restores a deal is stamped after its deletion. A missing or repeated id is derived from the record, so every tab gives it the same id. The edit form saves only the fields typed in it, a field of the report only itself, and the preferences only the keys changed, with any key a refused write left unwritten: it stays this tab's until a write stores it, unless another tab stores that key first, when the later act stands: the names and the price record take the stored value, and the structure and worksheet in use stay this tab's, unstored. A save from the console writes the fields changed in that tab (each input, each term of the financing structure, each worksheet cell) over the store's copy, and a field another tab saved that this tab has not changed is taken up; where both tabs changed one field, this tab keeps its value and the page says so. Every read of the store (another tab's save as it is heard, the Deals tab and its actions, an export, the report, an import) brings the deal in the console up to it the same way, and a deal deleted elsewhere keeps its name, business, recipient and worksheet for the next save, which says why; restored from a backup, it is the console's again, with this tab's changes over it: one the store refused, and the business and recipient typed while it was lost. A change the store refuses stays in this tab, field by field, until a write succeeds; merged over another tab's newer save, it is a new edit, stamped after both. A record with no time of its own, or one more than a day past this computer's clock, is older than any copy or deletion; a reload applies the deletion list, and a deletion the store cannot take is not recorded either. A stored list that cannot be read is copied aside before a save can replace it; with no room for the copy nothing is saved over it until it is downloaded as a file and the broker says the file is kept. Other tabs redraw when the store changes, the Deals tab's fits only while it shows;
  - deals export to JSON and CSV and import from JSON.

### The financing check
- **The rules** are read from SBA's own SOP 50 10 8.1 (the docx and the procedural notice on sba.gov). Appendix 15 governs 7(a) changes of ownership for applications numbered from October 1, 2026. They are published rules, labelled aggregate:
  - **Transaction types,** three of Appendix 15's four categories. A business expansion is a business operating 2+ full fiscal years under its current owners buying all of one in its own 4-digit NAICS industry group. An owner buyout is owners or employees active in the business for the last 24 months buying out an owner; anyone else may take under half and not become the largest owner, or the deal is an initial acquisition. The fourth category, a purchase by an ESOP or a cooperative, has rules of its own that the check does not model. Anything else is an initial acquisition.
  - **Coverage.** At least 1.25× debt service coverage for an initial acquisition or an owner buyout, and 1.15× for a business expansion. It is tested on the last fiscal year or the average of the last two, historical or adjusted (Para. C.2.b), on the highest level of financial reporting the business has, tax returns last, or on a Quality of Earnings report's earnings where one is required; IRS transcripts verify the figures.
  - **Equity.** At least 10% of the total project cost; for an owner buyout, 10% of the price. Seller debt on full standby for the life of the loan may supply at most half of it. For a business expansion or an owner buyout the lender may reduce or eliminate it when the business keeps the liquidity and working capital to run, with no negative net worth, and a loan whose equity is eliminated may not fund working capital; for an initial acquisition it cannot be reduced.
  - **Loan terms.** Amortization of at most 10 years without real estate. The maximum Standard 7(a) loan is $5,000,000.
  - **The debt cap.** All acquisition debt, including a seller note not on full standby, is limited to the business valuation; any price above it is paid in equity: cash, or a seller note on full standby. The check counts the working capital, closing costs and guaranty fee financed in the loan as acquisition debt, as the cap is on the total, and says so (round 9).
  - **The guaranty fee** (13 CFR 120.220; FY2027 rates, Information Notice 5000-881797, round 9). A share of the loan's guaranteed part (85% of a loan of $150,000 or less, 75% above): 2% to $150,000, 3% to $700,000, then 3.5% of the guaranteed part to $1M and 3.75% above. Waived on loans of $700,000 or less to manufacturers, listed food-supply businesses and rural businesses. Financed in the loan unless set otherwise, so the loan, its payments, the debt, the equity base and the $5M maximum carry it; paid in cash at closing it adds to the buyer cash.
  - **Due diligence.** The lender may value a business priced at $350,000 or less itself, unless buyer and seller have a close relationship, such as existing owners or family (Para. C.1.a): an owner buyout between existing owners is one, and the check says so for an owner buyout at that price. From a $3M price it also needs a Quality of Earnings report, except for an owner buyout (SBA's, a minority sale to anyone else included) or an ESOP or cooperative purchase.

  Paragraph letters are cited only where SBA's own cross-references give them. The other rules are cited by section name.
- **Coverage** is SDE, less the new owner's pay and any capital spending, over a year of payments on the SBA loan and the seller note (none when the note is on full standby).
- **Two of the console's tables are reused:**
  - **The rate** is today's prime plus the fitted SBA spread, read on the loan's own size. The prime moves no model figure; this is its one reader.
  - **The new owner's pay** defaults to a general manager's market pay for the industry and size (BLS OEWS, aggregate; reading it at the firm's size rank is judgment), with the employer's payroll taxes and benefits (×1.24, BLS ECEC, the loading the console's GM hire uses), because SDE adds the seller's back.
- **An owner buyout of part of the business** (round 9) takes a share from 1% to all of it: the price of the interest bought, the valuation its debt may not exceed and its equity are the whole business's times the share (the model value has no minority discount). Every other type buys the whole business.
- **The starting structure** is 10% buyer cash and a 5% seller note at 6% over 10 years. The cash is SBA's minimum; the note is a common structure (judgment). Every part is editable. Shares are kept to 0.01% and the note's rate to 0.01 points, the precision their boxes echo, whether typed or stored, and an amount is none or at least a dollar.
- **The table** shows each ask (the two optimizer asks, one column when they print as one price, as on their card and in the report, and the broker's own, which shares a column only at the same price) as price, loan, note, cash, acquisition debt (flagged above the model value), payments, cash available and coverage. Coverage prints rounded down, so a ratio just under the minimum never reads as the minimum, and SBA's minimum grades it only where there is an SBA loan. With no loan a note on full standby has nothing to stand behind, so it is paid on its own terms.
- **The highest price this structure finances** is the highest price at which coverage meets the minimum and the acquisition debt stays within the model value, which stands in for the lender's valuation, with the shares as typed. A scan in 5% steps from the first price that carries an SBA loan finds the first price that fails, and a bisection its edge. The search stops where the loan reaches the 7(a) maximum: past it the shares no longer hold, since the rest of the price would be buyer cash. It prints rounded down, so the price shown passes its own tests, and the box names what binds (coverage, the value or the cap). Working capital makes the equity share move with the price: with a standby note's credit, an initial acquisition or an expansion passes only from some price up; alone, an owner buyout passes only up to some price. The box names that price, the first passing price rounded up and the last rounded down, so each passes as printed. The edges are found only over prices that carry an SBA loan, and when the floor and the highest price, rounded, would cross, both print in whole dollars. Past the 7(a) maximum the rest of the price is buyer cash, so an equity short there comes back where buyer cash reaches 10%, which the box names for an initial acquisition and for an owner buyout whose equity stops passing below the cap; with a paid seller note of about 90% of the price it never does, and the box says the equity is short at every price. For an initial acquisition a structure short of 10% works at no price below that. With no equity at all the lender would have to eliminate the requirement, and SBA then bars working capital from the loan: the box says so. When the working capital and closing costs in the loan alone take more payments than coverage allows, the box says that, not that the business covers no loan.
- **Notes** cover equity short of 10%, debt above the model value, the QoE threshold and the lender's valuation.

### The add-back worksheet
- **Input.** Up to three years, most recent first.
- **Calculation.** SDE is income before income taxes, plus:
  - one working owner's pay with its payroll taxes and perks;
  - depreciation and amortization;
  - interest;
  - income taxes deducted above the income line (state and local, or a pass-through entity tax);
  - one-time, personal or above-market items.

  It subtracts non-operating income and the pay to bring any other working owner to market. Expense lines are read as amounts spent, so "(12,000)" there adds back 12,000; a "Less" line always deducts, and says so when given a negative.
- **Line names, not line numbers, for each source,** with what each form already leaves out (interest, capital gains, charitable gifts and section 179 on a pass-through's Schedule K; payroll tax on the owner's or a partner's own pay, which Schedule C and Form 1065 never deduct) and what it puts elsewhere (officer pay in cost of goods sold, on Form 1125-E; a C corporation's charitable contributions, inside its starting line; another partnership's ordinary income, inside the starting line of Form 1120-S, Form 1120 and Form 1065 (a sole proprietor reports it on Schedule E), a deduction; the energy efficient commercial buildings deduction, Form 7205, a capital cost expensed as section 179 is, an add-back):
  - Form 1120-S, Form 1120 and Form 1065;
  - Schedule C, whose owner's pay is the net profit itself;
  - an income statement.
- **Basis.** The most recent year, a 3:2:1 weighting, or an average of the years entered. Weights go by column, so with the most recent year's revenue alone they are 2:1, and with the middle year blank 3:1; the report and the worksheet state the weights applied.
- **Warnings** (judgment thresholds that change no figure):
  - one-time and discretionary add-backs (the items above zero) over 15% of SDE;
  - SDE more than 15% below the year compared, named;
  - no positive earnings;
  - a Schedule C owner's pay counted twice;
  - payroll tax on the owner's own pay, or income taxes, that the source never deducted;
  - an expense or a deduction typed as a negative;
  - a year with revenue alone, named: it stays out of SDE, and sets the growth only as one of the two most recent years.

  The report states only the flags of the years the SDE's basis reads, naming the amounts added back. Two amounts in one box (a comma and a space, a second dollar sign, a tab, a line break, two kinds of space) are refused in every money box, as is a column or row of cells pasted and a negative revenue; a number grouped with plain, no-break or thin spaces, one kind throughout, is one.
- **"Use in the console"** sets SDE, revenue and, if wanted, growth. It leaves the ask alone. A figure past the console's range is held to it, marked as a typed one is, and named in the message, which echoes each figure as its box shows it.

### The seller report
- **One page,** with:
  - the model value and its quality position;
  - the 80% range if it sells at the recommended ask, and the model's accuracy;
  - each ask with its chance of selling, median time, median price, expected proceeds and lender coverage, and beside the patient-seller ask the console's qualifiers: the ask cap, a judgment, from the printed 1.44×, where the soft cap's rounded corner sets the ask; a range when another ask is close to a tie, which says when its top is the cap or where the cap binds; a coin toss when it gains under 1% of value;
  - what a buyer's lender will see;
  - the three largest value drivers and up to three changes that pay for themselves, each measured, as the report says, with the ask reset to the recommended ratio of the value after it;
  - the earnings basis, when the worksheet set the SDE;
  - the sources and a disclaimer.

  Every figure carries the console's badge for it. Where a judgment input also moves a fitted or published figure (the quality position, the price-gap penalty above value, the overpricing time multiplier, the seller-note convention and the pay's rank, and the starting note's share where it sets a price the report derives from the 7(a) maximum or SBA's 10% rule (the highest price at the maximum, the prices past it where the share moves them, the equity's edge a standby note's credit sets) or the debt above value (on full standby below the maximum, where it sizes the loan, and a paid note past it, where the loan stays at the maximum)), the badge adds "× judgment"; coverage's own badge follows what moves it (the SBA rate's fitted spread where there is a loan, the market pay, the seller-note convention), and the footer names each judgment input behind a badge, the highest financed price's included. An extrapolated value carries the console's warning. Each value lever is the model's own gain for one peer step toward its best (the unit the console's sensitivity ranks every lever in, selects included), for the room left before its best when that is nearer, or, when a step does not register, at its best with the reason: the factor's own z sits at or past its limit, so the step leaves it there or lifts it a sliver; the business sits past the bottom of the quality range; or, for any other reason, the step's size. Every lever whose best adds over 0.1% of the value is named, unless three larger lines are. A line groups only levers the model weights alike; a lever with no room or no gain is not offered, and a business past the bottom of the quality range is told what all nine factors at their best would add, beside any lines.
- **Text typed into the report is escaped.**
- **The paper** has its own stylesheet, which reverts the page's styles inside it. The page holds it under the paper's id, so no page rule outranks it, and the page's few `!important` rules stop at the paper: the preview and the print lay out exactly as the downloaded `.html` file does, and the browser test compares every computed property of every element. The file has no script and no link.
- **Printing** while the report is open prints the paper alone, on Letter with .3in top and bottom margins and .4in at the sides. It fits one page. In print the business name holds to two lines and the block after it, the date first, to three, so names at the fields' 120-character limit fit too; a business name over 28 characters, or a block over 120, prints at the smaller size, so no shorter name prints taller. The tallest report the searches of rounds 5 to 8 could reach, past the bottom of the quality range at the ask cap with realistic names at the fields' limit, measures 1,004 px against the page's 998 and prints on one page (the paper measures a few px over the page and still prints whole). The browser test prints it and the tallest the reviewers found, with 120 W's in each name, from the page and from the file, and checks the PDF's page count.
- **Remembered fields.** The broker's name and firm are kept for the next report; the business and recipient are kept with the deal.

### Saved deals
- **What a deal holds:**
  - the console's inputs, its financing structure and its worksheet;
  - its status (valuing, listed, under LOI, closed, withdrawn, expired);
  - its listing price and date, and its sale price and closing date;
  - the cash at closing, the buyers contacted, the offers received and notes.
- **The comparison is with today's model,** run at each deal's listing price.
- **The track record:**
  - **Sale price** over the model's expected price if it sells, at the listing price, from 3 closed deals: the mean of the ratios, which is 1 for deals that sell as the model expects. Its 90% interval pools the deals' own spread with the model's, counted as ten deals, and reads Student's t.
  - **Time to close** over the model's median, from 3 closed deals with both dates, with or without a sale price; a closing date after today is flagged and left out until it is corrected.
  - **The close rate** of finished listings against the rate the model expected at those prices, from 5.
- **The opt-in price record** shows beside the console's value and in the report. It is display only, read with the weight of ten deals toward the model (`CALIB_K`, judgment).
- **What the deals can fit:**
  - **The price-gap penalty's scale** (0.45, judgment), fitted together with the broker's own close rate at value by maximum likelihood (a grid refined by golden section, since each listing's 95% cap can give the likelihood more than one peak), with a 90% profile-likelihood interval, once 20 finished listings include 5 listed at least 10% above value and 5 at or below value, which fix the close rate (with none, every scale fits as well as any beside some close rate). A listing more than 200% above value, past the survey's range, is left out, and the card counts it. When every listing at value closed, the close rate is stated only as a lower bound.
  - **The nine quality effects,** by least squares, once there are 60 closed deals, leaving out a factor that never varies.

  Until then the tab shows the progress. The Data tab's "Still judgment" note now points to the Deals tab, and a new Data tab section lists every rule and convention the tools use, with its badge.

### Found while building
- **A deduction typed as "(12,000)" added $12,000.** It was stored as negative, then subtracted. A deduction line now deducts whatever its sign, and the box shows the amount.
- **"Save as new" showed with no deal open.** The buttons' display rule overrode the `hidden` attribute. Hidden now wins inside the tools.
- **The report's asks table overflowed the paper.** Its numeric-cell rule kept the headers on one line, and the printed report ran to two pages. The headers wrap, the badges sit under them, and print sizes were tightened, so it is one page.
- **Opening a deal from the Deals tab did nothing under reduced motion.** The nav's warp re-clicks the tab at once, and a browser ignores `click()` on an element whose own `click()` is still running. The tools dispatch the click instead, and it works with motion on and off.
- **On a phone the worksheet's labels ran off the card.** The page's `th` rule does not wrap, and the scroll mask then faded the third year. Labels wrap, and each line stacks its three years under its label below 640 px.
- **On a phone the deals table hid all but two columns.** It now uses the page's own card layout for tables.

### Tests
As first built; the skeptic review below added to them, and its table has the counts now.
- **Section 43 of model.test.js** (37 checks):
  - SBA's rule values;
  - the annuity and the loan's rate;
  - every coverage identity, including standby, equity by type, the 7(a) cap, the QoE rule and debt above value;
  - the highest financeable price: at the cap, at coverage, monotone, and moving the right way with cash, standby, type, capital spending and pay;
  - the worksheet's arithmetic, bases, deductions, blank years and warnings;
  - a deal's prediction;
  - the price, time and close-rate record on synthetic deals;
  - the penalty scale recovered from 4,000 simulated listings within four SEs;
  - least squares on an exact fit and a singular design;
  - the report's asks, its escaping, the opt-in line, the earnings basis and the stylesheet;
  - the page wiring.
- **tests/browser.broker.js** (new, 38 checks), in a real browser:
  - the financing check redraws without a console render, rejects bad entries and is remembered;
  - the worksheet's focus and Escape handling, its sums and its "Use";
  - saving and the "unsaved changes" mark;
  - the report's escaping and one-page print, and its self-contained download;
  - the Deals tab's edits, validation, two-press delete, JSON and CSV export (a formula-like name is written as text) and import (new, newer, older and invalid records);
  - opening a deal back into the console, and the opt-in record;
  - a reload;
  - blocked storage;
  - no sideways scroll at 390 px in the console, the worksheet, the report and the Deals tab.
- **Suites,** on the final build:

  | Suite | Result |
  |---|---|
  | `node tests/model.test.js` | 7,586 pass (7,549 before; section 43 is new) |
  | `node tests/fuzz.test.js 1500` | 179,746 checks pass |
  | `node tests/invariants.test.js --browser` | 253 invariants pass: statics 57, identities 60, extremes 60, app 76 |
  | `node tests/browser.inputs.js` | 15 checks pass |
  | `node tests/browser.sweep.js` | 121 input states at each of 1440 and 390 px pass (118 before: the sweep walks every console select, and the financing check's transaction type adds three) |
  | `node tests/browser.broker.js` | 38 checks pass (new) |

## Skeptic review of the broker tools, October 2026

The owner asked: "go through everything one last time with a team of skeptics and test invariants/sanity checks to make sure eveyrthing is correct.  repeat until it is 100% waterproof".

### How it ran
- **Each round** sends five reviewers, one per area: the financing check, the add-back worksheet, the seller report, saved deals, and the rest of the app (the core models, the page, the Data tab).
- **Each reviewer must reproduce** every finding with code it ran, and test invariants and sanity checks with code rather than by reading.
- **A skeptic per area** then re-runs each finding with its own script and tries to refute it. A finding counts only if its skeptic confirms it, in full or in part; one it cannot reproduce is refuted.
- **Rounds repeat** until one finds nothing new. Each round after the first is told what earlier rounds fixed, and checks those fixes too.

### Round 1: 66 of 69 findings confirmed
Two were high, 21 medium and 43 low. All 66 were fixed in one commit, each with a test.

- **Financing check (11).**
  - **The highest financed price ignored SBA's debt cap** (high). All acquisition debt, with a seller note not on full standby, may not exceed the business valuation. The price checked only coverage and the $5M loan. At the framework example it quoted $5.88M where the cap allows $4.50M. Over 500 SBA-sized businesses, 78% carried debt above value at the quoted price.

    The price is now the highest at which both tests pass, and the box names the test that binds. Above the 7(a) cap the search continues, because a paid seller note keeps growing there.
  - **The equity minimum was ignored.** A structure under 10% buyer equity, which an initial acquisition cannot waive, still got a price. Now no price works, and the report says why.
  - **The new owner's pay was a bare wage,** while SDE adds back the seller's payroll taxes and benefits. It now carries them (×1.24), as the console's GM hire does.
  - **Cash and a note over 100%.** Typed to more than the price, the note kept its full payments. It is now cut to what the cash leaves.
  - **Smaller defects:**
    - "no loan" and "no debt" contradicted the table;
    - coverage just under the minimum printed as the minimum;
    - an owner buyout was offered the lender's own valuation, which the close-relationship exception rules out;
    - the type labels dropped SBA's conditions;
    - a changed structure was not marked unsaved;
    - the pay was labelled fitted;
    - "1" meant 100% in a share box;
    - the lede claimed most buyers borrow under SBA's program, at any size.
- **Worksheet (16).**
  - **Hints that told users to double count.** The line hints told S corporation, partnership and Schedule C users to deduct income their starting line already leaves out. They also invited adding back payroll taxes that Schedule C and Form 1065 never deduct.
  - **State income taxes deducted above the income line** had no row.
  - **Signs.** A negative on a "Less" line was silently flipped, and add-back rows took impossible negatives.
  - **A revenue-only year** counted as $0 SDE.
  - **A rejected entry** kept a keystroke's prefix.
  - **Dragging the dialog's scrollbar closed it.**
  - **Growth past the rail's range** was capped without a word.
  - **Smaller slips:** Enter and Clear, accessible names, a stale SDE in deal names, gaps in the warnings, and a report that ran to two pages with long names.

  Every source now names each line and what its form leaves out. An income-taxes row was added. Expense lines read as amounts spent, and a deduction always deducts and says so.
- **Seller report (14).**
  - **Badges** were fixed where the console shows "× judgment".
  - **Missing caveats.** An extrapolated value was quoted with no caveat. A failed equity minimum and debt above value went unmentioned.
  - **Levers.** "What moves the value most" promised gains a lever at its best on the rail cannot give, and broke a seven-way tie by rounding.
  - **Stale state.** A report opened straight from a money box read the previous value, and a business name typed before saving was lost.
  - **Printing.** The Letter page size leaked into printing the console, and the worst case ran to two pages.

  Every figure now carries the console's tier. Levers with no room are left out and ties are one line. The worst case, with 120-character names and every optional section, prints on one page.
- **Saved deals (17).**
  - **The price record was biased** (high). It averaged log sale prices against the model's median of a distribution capped at the ask. A broker exactly on the model read 0.90×.

    It now compares each sale with the model's expected price, a mean of ratios, which reads 1.00 for such a broker. Its intervals, which covered 76% with three deals, now pool the deals' spread with the model's own, counted as ten deals. On deals drawn from the model they cover 95%, 93% and 91% with 3, 5 and 10 deals.
  - **The penalty-scale fit blamed the penalty for the broker's close rate.** It fixed the base rate at the model's, so a broker whose at-value listings close more often read as a smaller penalty. It now fits the broker's close rate alongside the penalty, with a 90% profile-likelihood interval. Over 500 simulated brokers that interval covers 89.6–91%.
  - **Smaller defects:**
    - duplicates copied a finished outcome, so a sale counted twice;
    - inherited names such as `constructor` passed cleaning and blanked the tab;
    - an unreadable stored record was deleted by the next save;
    - the time record required a sale price;
    - delete fired on one press after a redraw;
    - a factor that never varies stopped the quality fit;
    - impossible dates, booleans, fractional counts and repeated ids passed cleaning;
    - the CSV's model columns, error messages that named fields by code, and long names on a phone.
- **The rest of the app (8).**
  - **The Data tab's new section took Still judgment's place.** Moved after the live self-audit, it has its own id, index star, emblem and hue, and the seven sections before it keep theirs.
  - **Text corrections.** The prime-rate sentences now name the financing check as the prime's one reader. The overlaps with the other lanes (badges, the pay's label, the lede, the share boxes and exact echoes of entered amounts) were fixed with them.

### Round 2: 46 of 52 findings confirmed
Two were high, 9 medium and 35 low; six were refuted as harmless or by design. Three were found in two areas at once. Every survivor was fixed in one commit, each with a test that fails on the code before it: 27 of the browser checks and 16 of the model checks.

- **Financing check (14).**
  - **The highest financed price assumed unlimited buyer cash past the 7(a) maximum** (medium). Above the cap the rest of the price is buyer cash, so a paid seller note kept the debt test alive at 3 to 19 times the model value.

    The search now stops where the loan reaches the maximum, since past it the typed shares no longer hold. The box and the report say so and badge it as the published rule.
  - **"No price meets the 10% equity minimum" sat beside asks that met it** with buyer cash above the cap. The equity sentence is now bounded by the cap: the structure falls short up to that price.
  - **A merged "Your ask" column was read at the optimizer's price.** It now keeps its own column unless the prices are equal.
  - **Smaller defects:**
    - a failing share printed as the minimum;
    - cash and a note over 100% shrank the loan as the price rose;
    - "no limit" described a working-capital loan as one at the cap;
    - the owner buyout's 24 months, and the equity waiver's conditions, were missing;
    - a standby note was said to need buyer cash above the valuation;
    - the transaction types were cited to the wrong section;
    - capital spending went unnamed where it left nothing to cover;
    - a negative cash flow with no payments printed infinity;
    - two figures carried no badge;
    - the scroll chip covered the coverage row on a phone.
- **Worksheet (9).**
  - **Saving a deal after editing its own worksheet without "Use" dropped the worksheet** (high). The deal's worksheet is now the one in the dialog while it belongs to that deal.
  - **The Form 1065 hint told users to add back partners' retirement contributions** (medium), which a partnership never deducts.
  - **Smaller defects:**
    - a revenue-only year was said to set the growth when it set nothing;
    - the add-back share printed twice;
    - cells clipped 8-digit and negative amounts on a phone, and asked for a keypad with no minus sign;
    - "Use" without growth cleared growth's held-to-range mark;
    - below-market rent made the add-backs read negative;
    - the C corporation hint left out dividends.
- **Seller report (6, two shared with other areas).**
  - **"One peer step better is worth about $X" quoted the sensitivity's central slope** (medium, also found in the core area). Across a factor's ±3.2 z limit that promised $273k for a step worth $0. Each lever is now the model's own forward step, or the room left before its best.
  - **A business at the bottom of the quality range was told it sat at the top** (medium, found in the core area). The report now says where it sits and what all nine factors at their best would add.
  - **The worst case printed on two pages,** with the disclaimer alone on page 2. The page now has .3in top and bottom margins and tighter print lines. The tallest report the reviewers could reach prints on one page with about 30 px to spare, and the browser test prints that report.
  - **Smaller defects:**
    - with no SBA loan the note was graded against SBA's minimum, and a standby note behind no loan had no payments;
    - coverage's badge and the footer were fixed text;
    - a typing instruction reached the seller;
    - "−0% for quality";
    - "buyer cash pay".
- **Saved deals (12).**
  - **Two tabs of the page erased each other's deals** (high). Each save now merges with the store first, and the newer copy of a deal wins. Deletions are kept with their time, so an older tab cannot bring a deal back. Other tabs redraw on the storage event, and an edit form being typed in keeps its entries.
  - **The quality fit's panel ran 98 px past a phone's screen** (medium). Its columns can now shrink below their table, which scrolls.
  - **Smaller defects:**
    - stored inputs that were not numbers became a $1k business;
    - a half-typed date erased the stored date;
    - the report's draft names followed into another deal;
    - a sale typed ten times too high saved without a word;
    - the penalty fit's golden-section search stopped at a local maximum in about 2% of histories, and quoted a search bound as the close rate;
    - a record with no time replaced a newer copy;
    - a full store was blamed on a private window, beside "Saved.";
    - the report's names did not move the deal's time;
    - a duplicate kept a stale SDE in its name;
    - the penalty card read "7 of the 5".
- **The rest of the app (5).**
  - **Overlaps.** The bottom-of-range text and the lever slope, above.
  - **Echoes.** The worksheet echoed SDE as "$46k" under a box reading $45.5k.
  - **Data tab.** It now names SBA's fourth transaction category (ESOP and cooperative) as not modelled. Its lede now says which conventions are editable or opt-in.

### Round 3: 44 of 51 findings confirmed
Five were medium and 39 low. Seven were refuted, as harmless or by design, and four repeat another area's finding. Every survivor was fixed in one commit, each with a test that fails on the code before it: 26 of the model checks, 273 of the fuzz checks at 300 businesses, and 18 of the first 107 browser checks (the run then stops where the old merge has lost a deal).

- **Financing check (9).**
  - **An initial acquisition's equity was checked only at the highest price** (low). With working capital and a standby note the equity share moves with the price, so lower prices, the ask among them, failed SBA's 10% while the box quoted a price with no caveat. The check now finds the price where the equity starts or stops passing and names it. For an initial acquisition the structure works only from that price up.
  - **With no equity the box still financed working capital** (low, in part). The lender must then eliminate the requirement, not "waive part of" it, and SBA bars working capital from such a loan, though closing costs may stay in it. The box and the report now say "eliminates" and name the bar.
  - **Smaller defects:**
    - the highest price printed rounded to nearest, so the figure shown could fail its own test; it now prints rounded down;
    - the initial-acquisition label still said "a buyer new to this business";
    - the buyer-cash box echoed 9.96% as "10%";
    - the equation stated SBA's minimum with no SBA loan, and echoed typed amounts as "$91k";
    - with no loan the report said the cash "covered" 0.34× of the note's payments;
    - a ticked standby box with a 0% note was called "the standby note".
- **Worksheet (8).**
  - **"Save as new" dropped the deal's own worksheet** (medium). The copy now takes the worksheet in the dialog, from the deal it was made from, as does the Deals tab's new deal.
  - **Smaller defects:**
    - on the default latest-year basis the report stated flags from years the SDE does not read;
    - the report echoed SDE and its parts in whole thousands, so the parts stopped adding up (this held only outside $100k to $999k, where moneyIn is still whole thousands; round 9 prints the parts at the SDE's unit);
    - the officer-pay hint left out pay counted in cost of goods sold (Form 1125-E);
    - "512,000 470,000", or a pasted row of cells, became $512,000,470,000, in a cell or a rail box;
    - a negative revenue was averaged in;
    - an empty stored worksheet marked a deal unsaved;
    - two text slips.
- **Seller report (10).**
  - **The preview and the print did not lay out like the downloaded file.** Three of the page's `!important` rules, and rules more specific than the paper's own, reached the paper. Labels lost their capitals, table cells took the page's fonts, and the file printed 12 to 24 px taller than the page the test measured.

    The page now holds the paper's stylesheet under the paper's id, and the three rules stop at the paper. The browser test compares every computed property of every element of the page's paper and the file.

    Measured on the file, round 3's own added text had pushed the tallest reachable report past one page (1,027 px against 998). The print sizes are tightened, and three searches from different starts now top out at 953 px.
  - **A stale tab erased the broker and firm typed in another** (medium), and with them the worksheet and financing structure typed for an unsaved valuation. A preference save now writes only the keys it changed, and other tabs take up the names.
  - **Smaller defects:**
    - past the 7(a) maximum the equity sentence stopped at the cap, not where buyer cash reaches 10%;
    - a failing equity printed equal amounts ("$324k against $324k"), and a passing 9.5% share as "10%";
    - the track record scaled an expected price the report never showed;
    - the QoE exemption dropped SBA's 24 months;
    - with factors too far below their peers for a step to register, the report said every factor was at its best; it now names what each at its best would add;
    - "(weighted equally)" grouped levers the model weights differently;
    - "Your ask" merged with an optimizer ask within 0.5%;
    - the earnings basis said there were no payroll or income taxes to add back while its SDE had added them back.
- **Saved deals (12).**
  - **A deal stamped later than this computer's clock could not be edited or deleted** (medium). Each action said it worked and was then undone by the merge. An edit's time is now always later than the copy it was made from.
  - **Restoring a deleted deal from a backup was undone by any other tab** (medium). The restored deal is now stamped after its deletion.
  - **A tab that missed the storage event:**
    - dropped another tab's deletion when it deleted;
    - erased another tab's recorded outcome through its edit form or the report's business name.

    Deletions now merge before they are written, and the form saves only the fields typed in it.
  - **With the store full a deletion was not recorded** but the page said "Deleted", and another tab wrote the deal back. The page now says so.
  - **Smaller defects:**
    - entries typed in the edit form were wiped by a look at the console;
    - a stored record with no time lost its first edit;
    - "Save the console as a new deal" said "Saved" when it was not;
    - two tabs gave a record with no id, or a repeated one, different ids; ids are now derived from the record;
    - a deal with the id "__proto__" could never be deleted;
    - the penalty card quoted the fit's search bounds as fitted values;
    - round 2's "deaf tab" test heard the storage event after all.
- **The rest of the app (5).**
  - **Two stored deals that shared an id collapsed into one on the first save:** round 2's merge had undone round 1's fix. The derived ids keep both.
  - **Working capital whose payments alone break coverage** was reported as the new owner's pay leaving nothing. The box and the report now name the working capital.
  - **Overlaps:** a future time (saved deals), the labels and the QoE exemption (financing), and closing costs (financing).
- **Refuted, and what changed anyway.**
  - **Escape in a worksheet cell** keeps what was typed, as Close does. A cell applies as it is typed, so a revert would drop an amount typed in full.
  - **A select lever quoted at its next option.** "One peer step" is the unit the console's sensitivity ranks every lever in, and the options sit 0.8 to 1.2 steps apart. The report keeps the step.
  - **The type select clipping its labels** is cosmetic. The conditions moved to a line under the select anyway, for the confirmed label fix.
  - **Re-imported records with no id** are by design, as in round 2. The ids now derived from the record make the same record match itself on a second import.
  - **An empty worksheet marking a deal unsaved** was refuted as harmless in one area and confirmed in another; it is fixed.
  - **The fits running in a tab showing the console** were refuted as harmless. The storage handler leaves them to the Deals tab anyway.

### Round 4: 36 of 44 findings confirmed
Two were medium and 34 low. Eight were refuted, as harmless or by design, and four repeat another area's finding. Every survivor was fixed in one commit. Each one in the code has a test that fails on the code before it (16 of the model checks, 58 of the fuzz checks at 300 businesses, and 21 of the 162 browser checks); the one in this record was corrected.

- **Financing check (9).**
  - **The equity edges round 3 added printed rounded to nearest** (low). The price named as where an initial acquisition's structure starts working failed the unwaivable 10% as printed, and the price where an owner buyout's equity stops passing was overstated. The first now prints rounded up and the second rounded down, so each passes as printed.
  - **Past the 7(a) maximum an owner buyout's short equity was said to stay short at every higher price** (low), while the asks past the cap passed: there the rest of the price is buyer cash. The box and the report now bound the shortfall where buyer cash brings the equity back to 10%, as they already did for an initial acquisition. With a paid seller note of about 90% of the price buyer cash never reaches 10%, and both now say the equity is short at every price, not only below the cap.
  - **Smaller defects:**
    - a share typed past two decimals (9.996%) echoed as "10%" while the check read 9.996%; shares are now kept to 0.01% and the note's rate to 0.01 points, as typed or as stored, and a stored amount under a dollar is dropped, as its box drops it;
    - the table merged the optimizer's two asks within 0.5% of each other, while the report and the optimizer's own card used other rules; all three now merge them exactly when they print as one price;
    - with nothing left after the pay the equation read "= ≤ 0";
    - the transaction's conditions sat inside the select's label, so a screen reader read them twice, and the share boxes' basis was only a hover title; both are now visible text that describes its box once;
    - the Data tab said the check takes every owner buyout as a close relationship, while the page says one between existing owners is;
    - at the starting structure the highest price set by the 7(a) maximum was badged plain "published data", though the 5% seller note's share (judgment) moves it; it now adds "× judgment", and the footer names the convention for that price;
    - this record said working capital and a standby note move the equity share with the price; for an owner buyout working capital alone does.
- **Worksheet (7).**
  - **A worksheet typed for a deal after it was saved belonged to no deal** (medium). Saved from the console with no worksheet and given one afterwards, the deal showed nothing unsaved, "Update deal" wrote none, and opening the deal again dropped what was typed. "Save as new" and the Deals tab's new deal did the same for a deal with no worksheet. A worksheet edited while a deal is in the console is now that deal's own, and a deal saved with an empty dialog owns it.
  - **Two tabs on one deal** (low). A tab that had opened the deal showed "unsaved changes" once another tab saved its worksheet, and its next save put its stale worksheet back. A save now writes only the parts of the deal changed in that tab (its inputs, its financing structure, its worksheet). A part another tab saved and this tab has not changed is taken up, as the event arrives or at the save, which then says so.
  - **Smaller defects:**
    - "$45,000 $50,000", "512,000, 470,000" and the like still read as one number in every money box, while numbers grouped with no-break or thin spaces, and "$ 1 450 000", were refused; a dollar sign now counts only first or last, a comma only between digits, and any of those spaces groups digits;
    - the report said "weighted 3:2:1" when the most recent year had revenue alone (2:1) or the middle year was blank (3:1);
    - the report said Schedule C and partnership returns never deduct payroll tax; only the owner's or a partner's own pay carries none;
    - the hints left out another partnership's ordinary income, inside every return's starting line, and the energy efficient commercial buildings deduction (Form 7205), a capital cost expensed as section 179 is.
- **Seller report (4).**
  - **Past the bottom of the quality range, factors near their peers were called "too far below" them** (medium), and round 3's lines replaced round 2's statement of what all nine factors at their best would add. "Too far below its peers" now means the factor's own z is at its limit. A factor whose step does not register because the business sits past the bottom of the range says that, and the report gives the all-nine figure beside any lines.
  - **With all four names at the 120-character limit in the widest letter** the report printed on two pages, the footer alone on the second. In print the business name now holds to two lines and the block after it, the date first, to three.
  - **Overlaps:** the equity bound past the cap and the payroll-tax wording (financing and worksheet).
- **Saved deals (10).**
  - **Smaller defects:**
    - an edit form being typed in was wiped whenever its deal changed, by a save from the console, the report, an import or another tab; it now stays, says the deal changed, and its save keeps the other change;
    - a stored deal with no time of its own came back after its deletion; such a record is now the oldest against a deletion too;
    - the report wrote back the business and recipient it opened with whenever any of its fields changed, and the broker and firm on any change; each field now writes only itself, and the business and recipient another tab saves show in the open report;
    - with a full store a deletion was recorded though the deals were not written: the page said the change was not kept, yet after a reload the deal could not be edited and the next save removed it. The deletion is now not recorded either, the page says the deal is not deleted, and a reload applies the deletion list;
    - a deal stamped at the latest time a Date holds could be neither edited nor deleted; times now stop at the end of the year 9999;
    - "Save changes" on a deal deleted in another tab saved a new, generically named deal without a word; it now says so and keeps the deal's name and business;
    - a tab that missed other tabs' saves listed and exported a stale set; the Deals tab and the exports now read the store first;
    - with no finished listing at or below value the penalty card quoted a scale the listings cannot tell apart from the close rate; the fit now waits for 5 such listings;
    - stored and imported structures kept shares and amounts the boxes refuse (with the financing check, above);
    - and, found while checking the deletion, a second press of Delete could be undone by an earlier arming's timer.
- **The rest of the app (6).**
  - **With both optimizer cards at "do nothing", the proceeds card named the utility card's over-budget change, or none** (low): the two were one record. Each card now holds its own, and over 120 random businesses the proceeds card names what its own search finds in every case.
  - **Round 3's guards on the page-wide rules raised their specificity,** so eight hero figures lost their -0.01em tracking. The guards now add none.
  - **Overlaps:** the dollar sign, the no-break spaces (worksheet), the same-ask rule (financing) and the latest time (saved deals).
- **Refuted, and what changed anyway.**
  - **A 9.96% buyer cash read "10% of the project"** beside the box's 9.96%: the table prints shares to 0.1%, and no test reads the cash alone. Shares are now kept to 0.01% anyway, for the confirmed echo finding.
  - **The lede's "all the acquisition debt"** is the page's defined term, which leaves out a standby note, as SBA does.
  - **The coverage column's fixed "fitted × judgment"**, raised twice, labels the whole column, whose optimizer asks judgment moves (round 2's ruling).
  - **The console and the report merging the optimizer's asks by different rules** was refuted in one area and confirmed in another; one rule now serves both.
  - **The export's unreadable records**, dropped on import without a word: no page can read them, and the file keeps them.
  - **A highest price of $999,832 printing as "$990k"** is round 3's rule, rounded down at money's own precision.
  - **"−0.0%" on the console's quality band** is the page's signed-zero convention, refuted before.

### Round 5: 28 of 32 findings confirmed
Two were medium and 26 low. Four were refuted, as harmless or by design, and five repeat another area's finding. Every survivor was fixed in one commit. Each one in the code has a test that fails on the code before it (11 of the model checks, 53 of the fuzz checks at 300 businesses, and 16 of the 186 browser checks); the three in this record were corrected.

- **Seller report (5).**
  - **"What moves the value most" dropped a factor just past its z limit** (medium). Round 4 called a factor "too far below its peers" only when the step left its z exactly where it was. A factor between its -3.2 limit and about one step below it, whose step lifts its z a sliver, was then dropped, though its best added more than every line kept: retention worth $562k at its best for a software business at 34%, gross margin $1.12M at 21%. Near the top of the range the report said no factor moved the value while one added $11k. Every lever whose best adds over 0.1% of the value is now named: too far below its peers when its own z sits at or past the limit, past the bottom of the range when the composite is held there, and otherwise with the step's size.
  - **The patient-seller ask went onto the seller's paper without the console's qualifiers** (medium). At the 1.5× ask cap the console calls the ask a judgment, not an optimum; where another ask is close to a tie it gives a range; where the higher ask gains under 1% of value it calls the two a coin toss. Across 139 random states the console qualified the ask in 129 and the report in none. The report's row now carries the same qualifiers, from the same function.
  - **Smaller defects:**
    - "Worth doing before listing" quoted each change's gain on top of a reprice to the recommended ratio of the value after it, without saying so; the section now says so, and a report built without the console's ratio measures the gains at it too;
    - this record's tallest report was stale: round 4's bottom-of-range lines reached 1,004 px, about 6 px from a second page, and round 5's qualifiers then pushed one state onto two pages, the footer alone on the second. The print lines are a little tighter, and the tallest a new search reaches measures 998 px and prints on one page; the browser test prints it.
  - **Overlaps:** the report's fields with a full store (saved deals).
- **Financing check (5).**
  - **Smaller defects:**
    - with buyer cash just under 10% beside a 90% note the loan is under a dollar at small prices, which the check counts as cash: the box named an equity edge at $2k for every type, the sentence written for an owner buyout, and told an initial acquisition the lender may waive its equity. The edges are now found only where there is an SBA loan, and only an owner buyout's equity is said to stop passing;
    - the highest price rounded down and the equity floor rounded up could cross, so that no price printed passed ($266k and $267k for a window of $266,667 to $266,907); when they would, both print in whole dollars;
    - an owner buyout's failing buyer cash read "9.5%: under SBA's 10%" beside passing cells reading "8% of the project"; it now names its basis, the price;
    - a seller note on full standby at the starting 5% share sizes the loan, yet the highest price it set by the value or coverage, and coverage itself, were badged plain "fitted"; they now add "× judgment", and the footer names the convention;
    - this record said the box names, for every type, where buyer cash past the 7(a) maximum brings the equity back to 10%; it does so for an initial acquisition and for an owner buyout whose equity stops passing below the cap;
    - and, found while testing these with such a loan share drawn: at a 0.05% loan share the 7(a) maximum sits at a $10B price, where a rounding error read as a loan past it; and a 90% note on full standby, paid below the price where an SBA loan first appears, read "no price" though every financed price passed. The price named at the maximum is now a hair under it, and the search for the highest price starts where the SBA loan does.
- **Worksheet (5).**
  - **Smaller defects:**
    - two tabs that changed different cells or inputs of the same part of one deal erased each other's saved change without a word: round 4's merge went by part. It now goes by field, and where both tabs changed one field this tab keeps its value and says so, as it hears the other's save and again as it saves;
    - a tab that heard the deal in its console deleted saved it next as a new, generically named deal without its worksheet, while a tab that had missed the deletion kept them; every tab now says the deal was deleted and keeps its name, business, recipient and worksheet;
    - an import that updated the deal in the console was not taken up: the console showed "unsaved changes", a save credited "another tab", and an edit saved after it undid the import; any read of the store now takes such a change up, and the message names the import;
    - a column of cells grouped with no-break spaces, pasted, read as one twelve-digit amount; a grouped number now uses one kind of space throughout, and a paste with a line break or a tab between figures is refused in every money box and worksheet cell;
    - this record and a code comment said another partnership's ordinary income is inside every return's starting line; a sole proprietor reports it on Schedule E.
- **Saved deals (12).**
  - **Smaller defects:**
    - "Updated in this tab only" was not kept in this tab: another tab's save of the deal reverted the console and emptied its worksheet, and the export the message advised lost the change; a change the store refuses now stays in this tab, field by field, until a write succeeds, and the toolbar says so;
    - a tab that missed other tabs' saves duplicated or opened its stale copy, even of a deal deleted elsewhere; Duplicate, Open and Edit now read the store first;
    - such a tab opened, printed and downloaded the seller report with stale names; the report now reads the store and the preferences first;
    - with the store full, the business, recipient, broker and firm typed in the report were dropped without a word; the report now says so, and the preference saves behind the financing check, the worksheet and the opt-in record say so too;
    - stored deals that could not be read, with no room to copy them aside, were said to be copied, and the next save erased them; nothing is now saved over them until they are downloaded as a file;
    - a deal stamped at the end of the year 9999 could be edited but its edits no longer ordered, and its restore from a backup was counted and dropped; a time more than a day past this computer's clock now counts as no time, and an import is counted only if it is kept;
    - the penalty card left out listings more than 200% above value, past the survey's range, without a word; it now counts them;
    - an edit form vanished without a word when its deal was deleted in a tab whose save this tab had missed; it now says so, and the message stays until it is seen;
    - messages quoting a long one-word name ran off the page; they wrap.
  - **Overlaps:** the two tabs on one deal, the deleted deal, the import (worksheet).
- **The rest of the app (1).**
  - **Overlap:** the pasted column of cells (worksheet).
- **Refuted.**
  - **A note term typed with decimals** (10.04 years) is echoed as typed while its payments use whole months: amortization needs whole months, the difference is at most half a month, and no test reads the term.
  - **A one-time or personal expense in parentheses** deducts, by design and as the dialog says: only the six expense lines read an entry as an amount spent, and a negative one-time item is possible (a credit inside expenses).
  - **"45.000" read as $45** is the page's en-US reading, echoed at once; refusing dot-grouped numbers would be a locale change, not a fix.
  - **The deal form's counts reading "12,15" as 1,215** move no figure and are echoed at once.

### Round 6: 34 of 39 findings confirmed
Two were medium and 32 low. Five were refuted, as harmless or by design, and four repeat another area's finding. Every survivor was fixed in one commit. Each one has a test that fails on the code before it (19 of the model checks, 5 of the fuzz checks at 300 businesses, and 21 of the 217 browser checks).

- **The rest of the app (3).**
  - **The patient-seller range left out the 1.5× cap** (medium). At the framework example (75% kept, $900 a day) the note under the listing cards, and since round 5 the seller report, read the patient seller's ask as 1.20–1.26× value. The cap is a third real peak, 0.38% of value below the walk-away ask with a 0.26% dip between, inside the page's 1% tie. The two judgment scales the note names as deciding between the ends, the scatter at high asks and the price-gap penalty, move the walk-away ask to the cap (FAN_S 0.95 or PEN_MAX 0.41). The note kept only the best of the near-tie peaks. Its range now spans every real peak within 1% of value with the walk-away ask, 1.20–1.50× here, and names each, the cap as the cap; the report reads the same range. The model tests found the same gap at five other states they scan, so the Data tab's "the console shows both ends as a range when they are within 1% of value" was false until now. The invariant suite's check of the note's range now reads the span.
  - **Smaller defects:**
    - with the store full or blocked, a change to the financing structure said it was not kept only in the toolbar, about 16,000 px above the section, and for 7 seconds; the section has its own status line now, which stays until a save succeeds.
  - **Overlap:** the seller report's paper in a tab that missed another tab's save (seller report).
- **Saved deals (12).**
  - **A change the full store refused, merged over another tab's newer save, kept that tab's time** (medium). The next write that succeeded here (deleting a deal, as the full-store message advises) stored the change at a time equal to the other tab's copy, so that tab never took it up, its next save of any deal wrote its own copy back, and the export the message advises skipped the change on import as not newer. Such a merge is now a new edit, stamped after both copies.
  - **Smaller defects:**
    - when the full store refused both tabs' changes to one deal, the one written first carried its earlier refused time, and the other tab, judging the store by its own later refused copy, never took it up and wrote its unchanged fields over it; a refused change is now merged whenever the stored copy changed since the copy the change was made from;
    - in that merge a field both tabs changed kept this tab's value without the clash message the normal path gives; it now says so, as it hears the other tab and again as it saves;
    - in that merge this tab's automatic name, moved by its own refused SDE, replaced a name typed in the other tab and froze; a name now merges with its automatic flag, and an automatic one follows the merged inputs;
    - a take-up of another tab's save cleared every held-to-range mark on the rail, though the held values stayed; it now clears only the fields it took up;
    - a deal deleted in another tab and restored from a backup stayed lost here: the message still said it was deleted, and the next save made a second deal of the same name; the console now takes the restored deal back, says so, and saving updates it;
    - "Download them" wrote over the unreadable deals right after starting the download and said it was done, though the page cannot know the file was kept; nothing is saved over them now until the broker says the file is kept;
    - a second tab opened on the same unreadable store still said the deals stored here could not be read after another tab had saved over them; it keeps its copy, which may be the only one, and now says what happened;
    - Reset in a tab that missed the deletion of the deal in its console called the deal unchanged in the Deals tab; it reads the deletions first;
    - with the store full, merely opening a deal said "the change is not kept"; a refused preference (the structure and worksheet in use, the broker and firm, the price record) now says what is not remembered after a reload, and that it applies in this tab.
  - **Overlaps:** the cell being typed in rebuilt by a take-up (worksheet), the report's paper (seller report).
- **Worksheet (7).**
  - **Smaller defects:**
    - a worksheet left in the dialog after Reset or a reload belonged to no deal, and when the deal in the console got its own from another tab or an import the dialog kept the leftover; one edit then made it the deal's and the save wrote it over the other tab's. Such a leftover now gives way to the deal's own when it arrives;
    - the lasting messages, that the deal in the console was deleted in another tab or that both tabs changed one field, stayed after Reset or after opening another deal, stating what a save would do to a valuation no longer shown; they now go with their deal;
    - Clear in one tab and a new cell from another reset the merged worksheet's source and basis to S corporation and "most recent year", which neither tab chose; emptying the cells no longer counts as changing those settings;
    - a take-up that put another tab's SDE above 92% of this tab's revenue held it there silently and said the console showed the other tab's change; the held SDE is now marked and named, as a typed one is;
    - "Save the console as a new deal" in a tab that missed the deletion of the deal in its console saved a generic deal without its name, business and worksheet; it reads the store first, as the toolbar's save does;
    - another tab's save of the same deal's worksheet rebuilt the cell being typed in: its text reformatted, the caret at the start, and the rest of the number refused, or a part-typed amount deleted; the cell now keeps its text, caret and the value it held when focused, and the dialog says what changed.
  - **Overlap:** the report's paper (seller report).
- **Seller report (6).**
  - **Smaller defects:**
    - "too far below its peers for one step to register" was given to a factor at its z limit whose step lifts it almost a full sd, which registers nothing only because the composite stays past -3, the reason another factor on the same paper got; "far" now needs the step to leave the factor's z at its limit or lift it under half a step;
    - the print sizes went by character count, so a business name of 56 characters or fewer, or a prepared-for block of 150 or fewer, could wrap at the larger size and print taller than the 120-character names the test used: round 5's tallest report, with 56 and 50 W's, printed on two pages. The smaller print size now starts where the larger could wrap: a business over 28 characters (37 W's fill a line), a prepared-for block over 120 characters, date and words between included (two lines hold 142 of the widest letters);
    - in a tab that missed another tab's save, committing a report field took the save up into the report's data but left the paper drawn on the old figures, so Print and Download disagreed, and the other name field stayed stale; the paper is drawn again, the untyped fields follow the deal, and the take-up message shows in the dialog;
    - when the two optimizer asks print alike, the report's one row said only "If you need to sell"; it is labelled for both sellers and gives the share kept and the cost of delay the walk-away ask counted;
    - after a report field the full store refused, a later field that saved left "the change is not kept" in the report and "kept in this tab only" in the toolbar; a write that succeeds now takes both back, and the toolbar follows each write;
    - the footer named the seller-note convention for "the highest financed price" in a report that prints none (an initial acquisition short of equity at every price); it now names the prices past the 7(a) maximum that the report prints, and badges them.
- **Financing check (6).**
  - **Smaller defects:**
    - text dragged into a money box got past round 5's paste guard: Chromium joins a dropped selection's lines with a space, so two cells read as one amount ($91,450 of pay); a drop is now refused and marked as a paste is;
    - with the note on full standby at the starting share, the debt above value moved with that convention but carried only the value's badge, and its repeat in the asks table none; both carry "× judgment" now (the table's line, shortened to "debt $X over value", keeps the report on one page), and the footer names it;
    - round 5's "no whole-dollar price" ignored that an expansion's or an owner buyout's equity can be waived: where the highest price and the equity floor share one whole dollar, every price up to it passes the other tests; the box and the report now give it with the waiver, as at every neighbouring SDE, and "none" only for an initial acquisition;
    - the report relied on an equity waiver ("if the lender waives part of the 10% equity") without SBA's conditions when no other sentence on the paper stated them; it now states them;
    - the failing buyer cash printed rounded to nearest in the table beside the equity note's rounded-down figure ($284k beside $283k, and at 9.99% the minimum itself); a failing cell now rounds down too;
    - the footer's Quality of Earnings exemption covered only buyers active in the business for 24 months; SBA exempts every owner buyout, a minority sale to anyone else included, and ESOP and cooperative purchases. The footer, the console's note and the Data tab now say so.
- **Refuted.**
  - **A deal restored from a backup in another tab** was refuted in one area (nothing lost, and the message's statements stay true) and confirmed in another (the message misleads and a same-named duplicate follows); the console now takes the restored deal back.
  - **The take-up pairing one tab's revenue with the other's SDE above 92% of it** was refuted as the console's own rule in one area and confirmed in part in another, for the silence; the hold is now marked and named.
  - **The report's "read on the most recent year"** beside a most recent column with revenue alone: the phrase reads as the most recent of the returns, the year the SDE reads, and the figure is right (round 4 ruled the same).
  - **A far extrapolation's "margin wider than usual"** is not on the report: the report's sentence already says the value is less certain than it looks at every distance, and prints each input against the data's 99th percentile.
  - **Two different imported records sharing an id** keep the newer: an id is a deal's identity across browsers, and the page's own export never repeats one.

### Round 7: 33 of 38 findings confirmed
One was medium and 32 low. Five were refuted, as harmless or by design, and seven repeat another area's finding. Every survivor was fixed in one commit. Each one has a test that fails on the code before it (13 of the model checks, 41 of the fuzz checks at 300 businesses, and 22 of the 248 browser checks).

- **The rest of the app (3).**
  - **Smaller defects:**
    - the console's note called a peak just under the ask cap, 1.48× or 1.49×, "the cap the console puts on the ask", though every other surface gives the cap as 1.50×, and beside a merged pair it named 1.49× the cap next to a range that ends at 1.50×. Such a peak is the soft cap's rounded corner, where the cap binds; the note now says so ("1.48× value (where the console's 1.50× cap on the ask binds)"), calls only 1.50× the cap, and keeps the label after the word "value".
  - **Overlaps:** the financing check's status line (financing check, saved deals), the marks of take-ups heard on the Deals tab (saved deals).
- **Saved deals (11).**
  - **A deal restored from a backup was re-attached over this tab's refused change** (medium). Round 6's re-attach took the copy this tab held, which already carried the change the full store refused, as the base of its take-up, so the restore's value replaced the change, the message said the inputs came back "as restored where this tab had not changed them", and a refused change to the deal's details was dropped without a word. The deleted deal's refused base also outlived it: the toolbar went on saying "kept in this tab only", and the next merge counted the backup's values as this tab's changes, so another tab's later change to one of them was called a clash and this tab's save erased it. The base is now the copy as stored when the deal was lost, so the refused change stays this tab's, in the console and in the details; a deal deleted elsewhere leaves with its refused base and clash parts; and another tab's later change is taken up without a clash.
  - **Smaller defects:**
    - the business and recipient typed in the report while the deal in the console was deleted elsewhere were dropped when it was restored; they stay, and are written as the report writes them;
    - a second tab on an unreadable store counted the deals another tab had since stored as in this tab only; it counts only those the store lacks ("1 of the 3 deals here");
    - a take-up that opening the seller report made was said in the toolbar the report covers, and the report's own line was cleared; one heard while the Deals tab showed was said in the hidden toolbar for 12 seconds. The report's line now says it, and a message heard with the console hidden waits until the console shows;
    - a listing price and a sale price both typed ten times too high saved with "Saved." and moved the price record from 1.00× to 2.43×; a listing far from the model value, or a sale far from the model's expected price at that listing, is now flagged;
    - the financing check's "not remembered after a reload" stayed after opening a deal had stored the structure in use; a preference write that succeeds now takes it back;
    - a broker's or firm's name the store refused did not stay in this tab: reopening the report, or any preference another tab saved, put the stored name back. A refused preference now stays until a write of it succeeds, and the next preference write that succeeds stores it, unless another tab has stored that key since;
    - a new deal the full store refused carried no "kept in this tab only", and deleting it said the deletion was not kept; it is marked, and its deletion is said to be done;
    - Reset in a tab that missed both the deletion and the restore of the deal in its console said it was deleted; it decides on the merged store;
    - a closing date after today was saved as a close and counted in the time record (638 days); it is flagged, shows no days, and stays out of the record until corrected;
    - the rail's held marks from take-ups heard on the Deals tab were kept in one slot: a second take-up dropped the first's, and a deal opened there inherited them. They now add up, a deal opened clears them, and a held SDE stays marked and named while it is held.
- **Worksheet (9).**
  - **Smaller defects:**
    - a take-up kept the old text in the focused cell even when nothing had been typed in it: the cell showed $40,000 while the worksheet, its total and the save held another tab's $55,000, and a refused entry put the old amount back over the other tab's save. A cell not typed in now shows the merged amount; in one typed in, a refused entry goes back to what the worksheet holds, and an entry kept over another tab's amount is a clash, said at once and at the save;
    - the dialog's lasting take-up message stayed after the save that settled it, on another deal and after Reset; it goes with its deal, and the dialog opens on what its own read of the store took up;
    - Clear saved in one tab reset the other tab's worksheet to S corporation and the most recent year (round 6's fix covered only a merge that left cells); the merged source and basis now stay;
    - a deal restored from a backup whose take-up held the SDE to 92% of this tab's revenue marked it but never named it, and the message went after 12 seconds; the hold and any clash are named, and the message lasts;
    - the worksheet dialog opened without reading the store, so a tab that missed another tab's save edited the stale worksheet, and a leftover from another deal was merged cell by cell into the one the other tab had saved; it reads the store first, as the report does;
    - "Save as new" and the Deals tab's new deal, in a tab that missed another tab's save, took the save into the console and the copy without a word; they say what was taken up, as "Update deal" does.
  - **Overlaps:** the marks of take-ups heard on the Deals tab and a deal opened there (saved deals), the restored deal's business (saved deals), Reset after a restore (saved deals).
- **Seller report (5).**
  - **Smaller defects:**
    - a report field stored in one place took back the refusal of a field the full store refused in another: a broker's name refused, then the business stored to the deal, left no warning, and the name was lost. A refusal is now taken back only once what it refused is stored;
    - at the default state the report's range ran to the 1.5× cap without saying so; a range whose top is the cap now says it is the console's cap on the ask, a judgment ("read it as 1.20–1.50× value; 1.50× is the console's cap on the ask (a judgment)");
    - an open report kept its price record after another tab recorded a closed deal or turned the record off, so Print and Download carried the old record; it follows the store, as the toolbar does;
    - the sources line printed the count of closed sales in the browser's locale ("18.941" in German) on an otherwise en-US paper; it prints "18,941" everywhere.
  - **Overlap:** the equity edges the starting note sets (financing check).
- **Financing check (5).**
  - **Smaller defects:**
    - past the 7(a) maximum the seller-note convention's badge was on the wrong figures: the loan stays at the maximum there, so a paid starting note's share moves the debt above value, which printed plain, while a standby note's moves neither the debt nor coverage, which printed with "× judgment" and the footer's entries. The badge now follows the note's effect, and the footer names the debt above value for a paid note past the maximum;
    - round 6 badged the prices past the 7(a) maximum only in the initial acquisition's "short at every price" sentence: an owner buyout's price where buyer cash brings the equity back to 10%, the equity floor a standby note at the starting share sets, and, with a typed note share, both prices past the maximum printed bare. Every price the report derives from the 7(a) maximum or SBA's 10% rule now carries "published data", with "× judgment" where the starting share sets it, and the footer names the prices past the maximum and the equity's 10% edge;
    - with storage blocked, the financing check's line said a deal saved with the structure keeps it, though nothing outlasts the tab; with a full store it now says a deal keeps it once its save succeeds, and with storage blocked it promises nothing;
    - the console's note said lenders test coverage "from tax returns checked against IRS transcripts", right under the note that a Quality of Earnings report's earnings are used from $3M. SBA's Appendix 15 reads the highest level of financial reporting available, tax returns last, and the QoE's earnings where one is required; transcripts verify. The note now says so.
  - **Overlap:** the line that stays after opening a deal stores the structure (saved deals).
- **Refuted.**
  - **A deletion said only in the toolbar while a dialog is open:** nothing the dialog shows or does depends on it, the message lasts and is beside the save it describes once the dialog closes, and the save says it again.
  - **"One step does not register past the bottom of the quality range"** where a step lifts the business out of the bottom repeats a part of round 6's finding that round refuted: every such step stays in the flat bottom of the range.
  - **The print thresholds** can be beaten only with characters no name contains (three-em dashes); names in ten wide scripts stay well inside them.
  - **The cap's label between "1.50×" and "value", and a range end the note does not name,** read unambiguously and come from the documented merge of candidates under two grid steps apart; the label now follows the unit anyway.
  - **A walk-away ask at 1.48× described as sitting at the 1.5× cap** is right: it is where the soft cap binds, not a measured optimum, and it moves with the cap.

### Round 8 (the last of the loop): 25 of 30 findings confirmed
One was medium and 24 low. Five were refuted, as harmless, by design or reachable only under the test harness's focus emulation, and six repeat another area's finding. Every survivor was fixed in one commit. Each one has a test that fails on the code before it (5 of the model checks, 1 of the fuzz checks at 300 businesses, and 13 of the 267 browser checks).

- **The rest of the app (3).**
  - **A walk-away ask or range peak the soft cap sets was presented as a measured optimum below 1.48×** (medium). Round 7 treated a peak as the cap's only above an unrounded 1.48, but the soft cap's rounded corner sets every walk-away ask and range peak from about 1.44×: they move with the cap (about 1.57× with the cap at 1.60×, 1.37× at 1.40×), and no peak independent of the cap lies above 1.44×. So the same card, "$2.06M, 1.48× value", carried the caveat and the flat top at $3,900 a day (1.4804) and neither at $4,000 (1.4790), though every ask from 1.25× comes within 1% of value of it, and a range top printed "1.48×" (1.4768) had no label on the console or the paper. A peak now counts as the cap's when it prints at 1.44× or more (`capSet`, from `RHO_BIND`, the cap times e^(−3.5K) of the soft minimum); there the note says it sits where the 1.50× cap binds, "test the market", and gives the flat top, the report's row gives the cap's qualifier, and a range top is labelled, on both surfaces, whatever the unprinted third decimal.
  - **Smaller defects:**
    - the console and the Data tab printed counts and amounts in the browser's locale: "18.941 closed sales", "2^11=2.048 combinations" and, in one Data-tab row, "$16.400" beside a written "$22,000" in a German browser. Every one of the page's 40 such calls now prints en-US, as the report's does;
    - a take-up heard while this browser tab was in the background was said for 12 seconds and gone before the broker came back, though a take-up is heard only in tabs other than the one that saved. It now waits, as one heard with the console hidden does, and its clock starts when the tab shows again.
- **Saved deals (7).**
  - **Smaller defects:**
    - a preference the full store refused was written at this tab's next successful preference write even when another tab had stored that key since: a structure or worksheet in use refused in one tab went back over another tab's later one, in tabs that heard every event, and a broker's or firm's name over another tab's later name in a tab that missed it. A refused key is now written only while the store still holds the value it was refused over; otherwise the later act stands (the names and the price record take the stored value; the structure and worksheet in use stay this tab's, unstored). A key refused again records the store it was refused over, so a name typed after another tab's save stays this tab's;
    - deleting a deal held only in this tab, beside other changes held there, said "the change is not kept", which reads as the deletion not kept; it says the deletion is done and that the other changes are still held here. The store line no longer says changes are kept in this tab only once none are;
    - a sale typed ten times too high got two near-identical tips, and the second said "at that listing" on a deal without a listing price; one sale gets one tip, and none names a listing the deal does not have (in part: the repeated tip was true);
    - a restore whose re-attach had already stored the business typed while the deal was lost said a save would write it; it says this tab's details are now stored over the restored ones, and keeps "saving here writes them" for what is not yet written;
    - Reset in a tab that missed another tab's rename named the deal as it was before the rename; it names it as stored (in part: "unchanged" means Reset left the deal as saved, which was right);
    - a tab that found a lost deal restored only through its own save said "Deal updated." after telling the broker the save would make a new deal; the save now says the deal deleted in another tab was restored from a backup.
  - **Overlap:** the report's line for a refused name (seller report).
- **Worksheet (6).**
  - **Smaller defects:**
    - a take-up while this tab's revenue held the SDE to 92% for display counted the display-only cap as this tab's change: it stored the cap, so the SDE stayed cut when the revenue went back, or kept this tab's old SDE over another tab's new one, which the next save erased. The take-up now reads this tab's SDE as typed and keeps an SDE it takes up as saved: the console shows it held to 92% of the revenue, marked and named, only while the revenue holds it, and the hold's sentence and mark go once the revenue leaves room for it. A hold that the other tab's revenue makes is named as well;
    - round 7 restored a focused cell's caret only where something had been typed in it, so a cell entered by Tab, its amount selected, lost the selection when another tab's save of a different cell redrew the table, and the amount typed next landed in front of the old one and was refused. The selection stays, all of it where all was selected;
    - a cell typed in and brought back to its committed text (a keystroke and Backspace) kept showing that text after another tab saved that cell, while the worksheet, its total and the save used the other tab's amount; it shows the merged amount, as an untyped cell does (in part: a retyped amount that differs is committed when the tab is left in a real browser);
    - deleting the deal in the console from this tab's own Deals tab left its lasting toolbar message, which described a save over a deal that no longer existed; the deletion takes it, with the clash and hold, as Reset does;
    - "Save the console as a new deal" in a tab that missed the deletion of the deal in its console said only that it saved the valuation; the Deals tab's line now says the deal was deleted in another tab and the valuation saved as a new deal under its name.
  - **Overlap:** a refused worksheet in use written over another tab's later one (saved deals).
- **Seller report (4).**
  - **Smaller defects:**
    - the report's lasting "not remembered after a reload" for a refused broker or firm went when the report was closed and reopened, and a take-up's 12-second message replaced it, while the name stayed unstored and was lost on reload. Reopening says it again, and a take-up's message keeps it beside it.
  - **Overlaps:** × judgment on the price where buyer cash brings the equity to 10%, and the footer for a coverage-bound highest price (financing check); refused preferences written over another tab's (saved deals).
- **Financing check (5).**
  - **Smaller defects:**
    - when every ask was past the 7(a) maximum and coverage bound the highest price below it, a standby note's starting share still moved that price, which printed "fitted × judgment", but the footer no longer named the seller-note convention: round 7 cleared it from the asks, its only source. The footer now reads the highest price's structure as well;
    - past the 7(a) maximum, for an initial acquisition with a standby note at the starting share and working capital, the price where buyer cash brings the equity to 10% carried × judgment, though the share does not move it (it is the same with no note at all); it now carries × judgment only where the starting share moves it, which the report checks numerically, and the price past which the loan stays at the maximum keeps it;
    - the report's coverage of the working capital financed in the loan, where no price works, printed bare beside badged coverage; it carries its badge;
    - a focused financing box kept the old structure through a take-up while the table, the report and a save used the other tab's, and a value typed while the other tab's save arrived replaced it with no clash; an untyped box shows the structure taken up, and a value kept over another tab's change to that box is a clash, said at once and at the save, as the worksheet's cells do.
  - **Overlap:** a refused structure in use written over another tab's later one (saved deals).
- **Refuted.**
  - **A seller note cut to fit the buyer's cash, badged × judgment at the starting share:** the starting share decides that the cash's shortfall is a seller note at all (at share 0 it is an SBA loan, with different coverage), so the coverage rests on the convention; the flip at a typed share is the page's general rule for typed figures.
  - **Text left in a worksheet cell after a take-up redraw** and **a refused entry in a cell another tab saved while it was typed** need an uncommitted, different text in a focused cell when the take-up runs, which only Playwright's focus emulation allows: in Chromium, WebKit and Gecko, leaving the tab commits the cell first.
  - **A hold one take-up names, named again after the revenue changed:** by design while the take-up stored the cap, since the SDE stayed held and marked, as a clamped typed SDE stays. Round 8's fix of the 92% take-up keeps the other tab's SDE as saved instead, so the hold now ends, sentence and mark, once the revenue leaves room for it, and is not named after that.
  - **The discretionary add-back warning at 15%:** the share is rounded correctly on both surfaces, and neither states the threshold or a verdict beside it.

### Round 9, a final review pass: 24 of 34 findings confirmed
After round 8 the owner asked for "one more comprehensive pass for any issues, particularly ones that will actually cause the outputted numbers to be wrong or mislead the user", to be listed first and not fixed, and then: "ok now fix all of them". Eight reviewers took one area each on 3c68fe2: the value model, the sale outcome and optimizer, the SBA financing check, the seller report, the worksheet and deal records, the console display, the Data tab and the inputs. A skeptic per area re-ran every finding with its own scripts and tried to refute it. Of 34 findings, 24 held (4 medium, 20 low) and 10 were refuted. Every survivor is fixed in one commit, each with a test that fails on the code before it (all 25 of the round's model checks, 4 of the fuzz checks at 300 businesses, and 11 of the 279 browser checks; the twelfth new browser check is that the page raises no errors).

- **Medium (4).**
  - **SBA's upfront guaranty fee was left out of the financing check.** The loan, its payments and coverage read about 2% to 2.8% optimistic, the highest financeable price 1.5% to 2.4% too high, and an ask within about 2.5% of the coverage edge read "meets 1.25×" though it fails once the fee is financed. The check now charges the FY2027 fee (SBA Information Notice 5000-881797, effective October 1, 2026): a share of the guaranteed part (85% of a loan of $150,000 or less, 75% above), 2% to $150,000, 3% to $700,000, then 3.5% of the guaranteed part to $1M and 3.75% above ($1,700 on $100,000, $138,125 on $5M). It is waived on loans of $700,000 or less to manufacturers (the console's manufacturing industry), listed food-supply businesses and rural businesses, which the new fee box can set. By default it is financed in the loan, the usual case: a project cost in the structure's own shares, so the loan, its payments, the debt, the equity base and the $5M maximum all carry it. Paid in cash at closing, it adds to the buyer cash and leaves the loan alone. The table has a fee row and a note, the report's lender paragraph names it, and the Data tab has its row. At $6M of revenue and $300k of SDE the highest financed price falls from $1.11M to $1.09M, and a $1.11M ask that met 1.25× reads 1.22×. With 10% cash and a 5% note, the price at the 7(a) maximum falls from $5.88M to $5.74M.
  - **"Medical or dental practice" was valued on the physicians' cell alone.** A dental practice read about 16% below the model's own dentists' cell, "Manufacturing" read the sign makers' cell and "Distribution" the lumber wholesalers'. Each industry is now valued on every BIZCOMPS 6-digit cell its label names, pooled as one cell: each cell's shrunk effect is taken back to its mean, the means and parents are pooled by count, and the pool is shrunk again with the same k of 25. The pools are physicians and dentists, four accounting and legal cells, every manufacturing (31-33) and wholesale (42) cell, two cells each for home services and staffing, six for auto repair, four food-service cells for restaurants, and construction's cells less home services'. A one-cell industry keeps its effect exactly. The framework example's value moves from $4.05M to $4.31M (+6.3%); the other pooled industries move by ×0.955 (construction) to ×1.117 (manufacturing). The Data tab lists each pool with its sales count. The risk model keeps one representative code per industry, and the confidence figure's comparables weight reads the pooled count.
  - **The two "overall outcome" cards disagreed.** The walk-away ask lists at once, while the optimizer's reprice is a relisting charged its 14 days at the cost of delay. So the optimizer card said "Do nothing — nothing within the budget clears its cost" beside a walk-away card naming another ask, though the reprice is free. When the reprice alone beats doing nothing before its days and not after, the card now says that: relisting at the walk-away ask, $X, adds $G but its 14 days cost $D at $L a day; before listing, list at the walk-away ask. It names an over-budget change only on a second line. In a 216-state grid, 137 of the 138 such disagreements are now explained; the one left is under a dollar of the objective apart.
  - **The report's caption defined expected proceeds as "the price times the chance of getting it".** The figure is the chance times the mean price if it sells, which the report never showed, and the chance times the printed median is 7% to 9% higher. The caption now says "the chance it sells times its average price if it does" and gives that price.
- **Low: numbers or claims a user could act on (15).**
  - the report's time column is the median time to close *if it sells*;
  - the report's expected proceeds are the whole consideration; each figure now says how much of it is paid at closing ("84% at closing"), as the console's hero does;
  - the report's accuracy label prints its meaning ("High: more predictable than three quarters of listed businesses");
  - the hero's EBITDA multiple read a sector wedge whose implied owner pay grew with SDE ($4.2M at one state), so a high-margin business showed about twice the multiple a buyer would pay. EBITDA is now SDE less a general manager's market pay with payroll taxes and benefits, the new owner's pay the financing check uses, and the tile says "EBITDA after a manager's pay" (none when that leaves nothing). The wedge now only converts EBITDA benchmarks to SDE, as the Data tab says;
  - the working capital, closing costs and fee financed in the loan count against the business valuation, as Appendix 15 caps the total acquisition debt. That reading is kept, and now disclosed in the table's note, the highest price's box and the report. Where the price itself is within the value, they also give the remedy: finance less of them in the loan (a line of credit sits outside it), pay the fee in cash, or add equity;
  - an owner buyout can buy part of the business: a share box (1% to 100%) prices the stake pro rata, caps its debt at the same share of the model value (which has no minority discount), and sets its equity at 10% of the stake's price. Every other type buys the whole business;
  - the track record never quotes a price above the ask it names, on the report and the toolbar;
  - the coverage and ROI equation panels plug in their figures at the input boxes' precision, so the fraction reproduces the printed result;
  - the worksheet's earnings basis prints its parts at the SDE's own unit, the largest part taking the rounding, so they add up as printed: no mismatch in 178,000 random worksheets, where about 1 in 4 tax-return worksheets missed by one unit. Round 3's fix of this held only outside $100k to $999k;
  - a typed revenue that holds the SDE to 92% of it marks the SDE box while the hold lasts, as every other hold path does;
  - the rail's percent boxes read a plain number under 1 as a share (0.72 is 72%), as the financing and deals boxes do; a percent sign keeps it as typed (0.5% is half a percent), and the boxes' tooltip says so;
  - the console's sources say the kill zone is 11-30% of the asking price, which is 12-43% over model value, the axis the console states gaps on everywhere else; the unused kill flag reads the band on that axis;
  - the Data tab's listing hedonic prints e^b − 1 with its standard error by the delta method: owner-operated −19% (se 4), where −21% was the log points;
  - the value gap's note gives each change it leaves out its own reason: outreach moves the proceeds, not the value; a change that lowers the value on its own says by how much; one that adds nothing once the other changes are made says that;
  - the peer bars are coloured by better or worse than peers, not by sign: more owner dependence or concentration than peers is rose, and the lede says which colour is which.
- **Low: wording and interaction (5).** The optimizer's lede names its first objective as expected proceeds, not price. The day counts the cards' note gives are the difference of the "Expected days" tiles as printed, and under two days the walk-away note gives tenths. The Data tab's Refused table no longer points to a table it does not show, or to evidence "above" that is below. Escape in a financing box puts its value back and applies nothing typed. The growth box asks for the keyboard with a minus sign.
- **Found while fixing.**
  - the fee's fixed point left a billionth of a dollar of buyer cash in structures with none, enough to call "no equity" some equity. It is cleared;
  - once the fee is financed, a paid seller note's share moves the debt below the 7(a) maximum too: a larger note leaves a smaller loan and fee. So the report's debt above value carries × judgment there at the starting share, and the fuzz invariant says so;
  - with this round's text the tallest report found reached 1,029 px, two pages. The caption and the lender lines are tighter, the cash at closing sits in the table cell, and SBA's waiver conditions print once: an equity edge after the Equity sentence points back to them. The tallest report found now measures 1,006 px and prints on one page.
  - two of the browser suite's two-tab storage checks (r6-deals-11, r7-deals-3) failed in some runs on the code before this round as after it: Chromium in this harness sometimes never passes one page's write of the store to the other page of its context (the second keeps reading the unreadable text while the first reads the deals it saved). Run alone, the first failed 2 of 6 times on 3c68fe2. Such a run cannot test the second tab, so both checks now try their scenario again, up to six times, until the second page sees the write, and say how many tries it took.
- **Tests re-derived.** Pooling moved figures the tests pinned, re-read from the live build:
  - two walk-away asks the Data tab quotes (1.16× at $400k and $4,000 a day, and the cap's knife edge at 82% kept);
  - the framework example's range (the cap within 0.37%);
  - the thetas of two walk-away flips, and the delay costs of the soft-cap checks;
  - the score pins;
  - the one-dollar equity window, now at $262,953 of SDE;
  - the staffing ratio's restaurant, now at $11M.

  The fee changed the financing identities: the project is the price and the fee, and the debt is 90% of both. Scenario tests built before the fee waive it, so they keep testing the structure they were written for. The confidence fit's own vectors are checked on a build that reads the representative cell, and the live weight against the pool.
- **Refuted (10).**
  - the extrapolation's rounding at 3×, which is the fit's own definition;
  - a future closing date in the price record and close rate, which is documented scope;
  - the note that "sets the growth" (by design);
  - the accuracy band's wording, a standard convention about 1 point off;
  - interior asks of a patient seller's range, which promise nothing (at most 0.21% over);
  - "the real decision" against a coin toss (documented, F-1);
  - "$0 a day of delay", which is true;
  - the anchoring formula's ρ̃, which reads correctly with ā;
  - typed decimals echoed rounded in notes, since the rule covers the boxes, which show them;
  - three console label slips, documented or harmless.

### Where it stands
| Round | Findings | Confirmed (in part) | Refuted | Fixed in |
|---|---|---|---|---|
| 1 | 69 | 66 | 3 | 6664c6e |
| 2 | 52 | 46 | 6 | f96e2ec |
| 3 | 51 | 44 | 7 | abd7e00 |
| 4 | 44 | 36 | 8 | 95b4935 |
| 5 | 32 | 28 | 4 | 4185ffc |
| 6 | 39 | 34 | 5 | 2f309d6 |
| 7 | 38 | 33 | 5 | 2388c6c |
| 8 | 30 | 25 | 5 | a631a70 |
| 9 (final pass) | 34 | 24 | 10 | this round's commit |

Round 7 still found one medium defect, so round 8 ran on 2388c6c, with every finding above as known. It was the last: the owner asked that the round under way at 1 PM on October 21, 2026 be the final one. Round 8 found one medium defect (the ask cap's rounded corner) and 24 low ones, all fixed in a631a70, and the loop stops there. No round came back without a medium finding, so the review ends at the owner's deadline, not at its stop rule. The owner then asked for one more pass, identify-only, aimed at figures that are wrong or mislead. It ran as round 9 on 3c68fe2, with eight areas instead of five, and its 24 confirmed findings (4 medium) are fixed. They have their tests, but no tenth review.

Suites on the round-9 build:

| Suite | Result |
|---|---|
| `node tests/model.test.js` | 7,816 pass |
| `node tests/fuzz.test.js 1500` | 214,359 checks pass |
| `node tests/browser.inputs.js` | pass |
| `node tests/browser.broker.js` | 279 checks pass |
| `node tests/browser.sweep.js` | 124 input states at each of 1440 and 390 px pass |
| `node tests/invariants.test.js --browser` | 253 invariants pass |

The tallest seller report found by two hill climbs from round 8's tallest states, with the guaranty fee and the stake among the mutations, measures 1,006 px and prints on one Letter page, from the page and from the downloaded file.
