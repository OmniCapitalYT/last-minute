# Audit findings: logic audit, ultracode round

These are the 25 defects that adversarial verifiers confirmed, each with a numeric reproduction, in the Phase 3 logic audit of `index.html` at commit 7cac297. Severity: 9 medium, 16 low. None were rated high.

Several findings were raised independently by different auditors and describe the same defect. They are listed separately, as confirmed, and fixed once. Overlapping groups:

- **A. Intervention table: closing probability is not constant across rows:** #3, #12, #17
- **B. Delay cost charged on the median but labelled E[T]:** #6, #13, #19
- **C. Optimiser U card: "different programme / less time and spend":** #11, #15
- **D. optNote lower branch: net gain shown as the value of time:** #14, #18
- **E. Closing-probability equation omits the tail, thin pool, size base and floor:** #5, #25, #16

The rest stand alone: #1, #2, #4, #7, #8, #9, #10, #20, #21, #22, #23, #24.

## Resolution

All 25 were fixed in one batch, in the commit that adds this section. Each has a pin in `tests/model.test.js` (section 29), and the new behaviour has invariants in `tests/fuzz.test.js` (7i-7n).

| # | Fix |
|---|---|
| 6, 13, 19 | The delay cost is now charged on the mean time to close, E[T] = t_med·(π/β)/sin(π/β) (`out.tMean`), in `bestRatio`, `optNote` and `optimize`. That is 28% above the median from $500K of value and 44% below it. `eq_t`/`eq_ts` show E[T]. The card tile is now "Expected days". The walk-away figures in the Data tab and the `bestRatio` comment are re-pinned: $900/day gives 1.13, 1.14, 1.15, 1.15; $4,000/day gives 1.09, 1.13, 1.14, 1.14; the cap wins from 77% / 76% / 80%; the interior margin is 0.46%; the FAN_S flip is about 0.915; the theta flip is about 0.771. |
| 9 | `businessScore()` prices the business at its optimal ask and at least the typical buyer pool. The caption splits what the Omni score loses into the ask's share and the pool's share. |
| 5, 25 | The 2% floor on P_C is removed, so P_C keeps decaying with the gap tail. `eq_p` now typesets the size-interpolated base, the piecewise penalty with its tail, and the thin-pool factor. The sensitivity note no longer says "pinned at its floor". |
| 16 | The P_C badge switches to "aggregate × judgment" below a typical pool, with a title naming the factor. The section lede, the Data-tab Model I lede, the footer and the expected-proceeds tooltip now mention the pool. |
| 3, 12, 17 | The ΔP_C column is restored. The footnote and caption now say the reprice equalises the gap, not P_C. |
| 11, 15 | The second card's subtitle comes from `optCardNote()`. It says "the same changes, repriced" when only the ratio differs, and names only the differences that move, in the direction they move. |
| 14, 18 | The lower-ask note prints the time value and the net gain separately. |
| 1, 2 | The quality row reads "percentile among peers, placed inside the measured p25–p75 band". The price rows name the realised-price fan. |
| 4 | The Data tab says P_C is quality-independent at the same ask relative to value, not at the same dollar ask. It also mentions the size base and the thin pool. |
| 7 | The time curve's `aria-label` says the curve is conditional on closing, and also gives P_C. |
| 8 | All 54 fitted states and territories are selectable. |
| 10 | The buyer chart, `eq_bs`, the table header and the `BUYERS` comment label the premium as over model value, not over a financial baseline. |
| 20 | The SDE margin range is read live: 20–30% at $200k SDE. |
| 21 | One `nAgg` count serves both the tally and the section badge. The SBA tail factor has moved from the fitted count to the judgment count, with its own inventory row. |
| 22 | The centring row of the self-audit uses a business at its peer medians, with revenue = SDE / fitted margin. It now reads in range. |
| 23 | The quarters are labelled "2020Q1–2021Q4, 2022Q2–2023Q3 and 2025Q4" everywhere, including `ttc_shape.source`, the fit script and the README. |
| 24 | `eq_v` and the Data-tab equation state that all amounts are in thousands of dollars. |

## Index

| # | Severity | Key | Title |
|---|---|---|---|
| 1 | low | `price:multbl:quality-percentile-mislabelled-as-spread-percentile` | Multiple table labels the quality composite percentile as a 'percentile of the measured spread', but the factor it shows is a different percentile of that spread |
| 2 | low | `price:multbl:stale-whole-spread-labels` | Median and mean price rows still say 'across the measured spread of value' after the fan was narrowed to FAN_S = 0.80 |
| 3 | medium | `closing:interventionTable:footnote-claims-PC-equal-across-rows` | The intervention table says the closing probability is the same in every repriced row, but outreach on a thin pool moves P_C by about 15 points and earnings changes move the size-keyed base |
| 4 | low | `closing:datatab:pc-quality-independence-claim-false-at-fixed-ask` | The Data tab says two businesses with identical financials and very different owner dependence get the same closing probability; at the same ask they do not |
| 5 | low | `closing:eq_p-eq_ps:formula-omits-tail-floor` | The closing-probability equations do not match the code beyond a 100% gap or at the 2% floor, and the floor freezes P_C and EVp again from about 28x value |
| 6 | medium | `timing:utility:median-used-as-E[T]` | Delay cost is shown as λ_T·E[T] but is computed on the median, which under the log-logistic curve is 22–31% below E[T], by an amount that depends on size |
| 7 | low | `timing:drawCurve:aria-label-unconditional` | The time-curve SVG's accessible label calls a curve that is conditional on closing the probability of closing |
| 8 | low | `risk:ui:state-dropdown-missing-jurisdictions` | The state dropdown omits 11 states, DC and 3 territories that have fitted effects shipped and counted |
| 9 | medium | `scores:render:business-score-counts-outreach` | The business score and its band caption treat the number of buyers contacted as business quality, so a top-quartile business is called 'below most peers' or 'bottom decile' |
| 10 | low | `buyers:labels:financial-baseline` | Model value is labelled a 'financial-buyer baseline', yet all three financial buyers plot above it as 'strategic premium' |
| 11 | medium | `decisions:optout-card:same-programme-called-different` | The utility card calls an identical set of changes "a different programme" and says it costs less time and spend, when it costs the same and takes longer |
| 12 | low | `decisions:interventionTable:footnote-pc-same-every-row` | The intervention table says the closing probability is the same in every row, but outreach on a thin pool moves it by up to 20 points |
| 13 | low | `decisions:utility-eq:median-labelled-ET` | The utility charges the cost of delay on the median time to close but prints it as E[T], understating the expected delay cost by 28-43% |
| 14 | low | `decisions:optNote:lower-branch-net-gain-as-time-value` | The lower-ask optNote presents the net utility gain as the dollar value of the time saved |
| 15 | medium | `optimizer:optout-card-U:false-time-and-spend-claim` | Second optimiser card says the walk-away programme saves time and spend when it saves neither |
| 16 | medium | `presentation:closing-prob:thin-pool-not-in-badge-or-captions` | Closing probability is still badged and described as conditioning on size and gap only, but the thin-pool factor scales it by buyers contacted |
| 17 | medium | `presentation:intervention-table:closing-prob-not-constant` | Intervention table footnote says the closing probability is the same in every row, and the caption cites a ΔP_C column that does not exist |
| 18 | medium | `optimizer:optNote-lower:net-gain-labelled-as-delay-value` | optNote 'lower' branch labels the NET utility gain as the value of closing sooner, which reads as a net loss |
| 19 | medium | `equation:eq_u:median-labelled-expected-time` | Utility equation charges delay on E[T] but the code and the substituted figure use the median time to close |
| 20 | low | `datatab:fitted-public:sde-margin-range-stale` | Data tab quotes the pre-shrinkage SDE margin range 18–35%; the shipped fitted medians are 20–30% |
| 21 | low | `datatab:tally:aggregate-count-mismatch` | Data-tab headline says 14 aggregate parameters while the Aggregate section says 17; the fitted tally also counts the tail factor the page labels judgment |
| 22 | low | `selfaudit:judgment-stack-row:tests-wrong-profile` | Self-audit row 'judgment-stack net adjustment for a business at its peer medians' reads 'off' because its profile is not at the peer median margin |
| 23 | low | `presentation:ttc:quarter-range-label` | '15 quarters (2020Q1–2023Q3 and 2025Q4)' names 16 quarters; 2022Q1 is not in the fit |
| 24 | low | `equation:eq_v:units-missing` | Value equation is typeset without units; taken literally in dollars it gives $0.73M instead of $3.28M |
| 25 | low | `equation:eq_p:penalty-cap-vs-tail` | eq_p bounds the gap penalty at 0.45, but beyond a 100% gap the code's tail drives it toward 1 |

## 1. Multiple table labels the quality composite percentile as a 'percentile of the measured spread', but the factor it shows is a different percentile of that spread

- **Key:** `price:multbl:quality-percentile-mislabelled-as-spread-percentile`
- **Severity:** low
- **Where:** index.html render(), multiple table row at line 4137 ('Quality position: ${ordn(qPct)} percentile of the measured spread' beside ×qFactor)

**Reproduction.** Default framework example (medical, rev $6M, SDE $1.45M, ask $3.24M) with node and tests/load.js: r.qPct 0.7857, r.qFactor 1.1709. The rendered row (Playwright) reads 'Quality position: 79th percentile of the measured spread ×1.171'. In the measured spread (fanRatio), ×1.171 sits at the 64.5th percentile; the 79th percentile is fanRatio(0.7857) = ×1.382. A top-quality profile (own .1, mgt .95, fin .98, rec .98, cc .02, ret .99, plt .02, grw .5, gm .9) has qPct 0.9987, labelled '99th percentile of the measured spread', with ×1.317, which is the 74.9th percentile of the spread (the spread's 99th is ×3+).

**Why it is wrong.** qf maps the peer quality percentile qp, from 0 to 100, log-linearly onto the interquartile band [p25, p75] = [0.727, 1.318] of the residual spread. qp is a rank among peers, not a position in the measured spread. The label tells the reader the business sits at the 79th percentile of where real sales land, which implies about +38%, while the model applies +17%. The hero quality band, in contrast, correctly says the inputs place the business inside the half-of-sales band.

**Fix (as proposed by the auditor).** Relabel the row, for example 'Quality position: 79th percentile among peers → ×1.171 inside the measured p25–p75 band'. Alternatively, show the residual percentile actually used (0.25 + 0.5·qp under the log-linear mapping, or the solved fan percentile).

## 2. Median and mean price rows still say 'across the measured spread of value' after the fan was narrowed to FAN_S = 0.80

- **Key:** `price:multbl:stale-whole-spread-labels`
- **Severity:** low
- **Where:** index.html render(), multiple table rows at lines 4147 and 4149

**Reproduction.** Rendered default: 'Median price if it closes — across the measured spread of value $3.24M' and 'Expected price if it closes — mean across the measured spread of value $3.10M'. The model computes both on R^0.80. Setting FAN_S = 1.00 (the measured spread) through the harness changes the default bear band from $2.64M–$3.16M to $2.29M–$3.05M, and E[P|close]/ask at the typical premium from 0.8895 to 0.8677.

**Why it is wrong.** The rows describe the whole measured value spread, but the figures use the calibrated realised-price fan (80% of that spread in logs). The hero tooltip, eq_s/eq_a and the Data tab were updated for FAN_S; these two labels were not.

**Fix (as proposed by the auditor).** Relabel to 'across the realised-price fan (FAN_S = 0.80 of the measured spread)' and 'mean across the realised-price fan'.

## 3. The intervention table says the closing probability is the same in every repriced row, but outreach on a thin pool moves P_C by about 15 points and earnings changes move the size-keyed base

- **Key:** `closing:interventionTable:footnote-claims-PC-equal-across-rows`
- **Severity:** medium
- **Where:** index.html render(): the #intbl footnote ('so the price gap, and with it the closing probability, is the same in every row') and the note at ~line 1887 ('ΔE[proceeds], ΔP_C and ROI are measured...'), against interventionTable() dP and model() thinF / fitClose base keyed on Vbase

**Reproduction.** Framework example (EX in tests/model.test.js) with buyers 25, s.rhoSell = bestRatio(s,0,0) = 1.100 and s.optRho as render sets them, interventionTable(s, model(s)): the repriced baseline has P_C 0.5043 (thinF 0.769). Rows: outreach dP = +15.11 pts (P_C 0.504 -> 0.655), margin +0.35 pts, gm -0.38 pts, growth +0.23 pts. Medical, $500k SDE, 30 buyers: outreach +12.12 pts, gm -0.56 pts. Fitness, $120k SDE, 20 buyers: outreach +14.66 pts. Even at 65 buyers: margin +0.25, gm -0.28, growth +0.17 pts (base interpolated on Vbase between $1M and $5M).

**Why it is wrong.** The ΔP_C column was removed because it was 'identically zero by construction (every row is repriced)'. That stopped being true once the thin-pool factor and the size-interpolated base were added. On a thin pool, the outreach row's whole effect is a closing-probability change, yet the table says P_C is the same in every row and the note above refers to a ΔP_C column that no longer exists. The ΔE figures are correct; the explanation of them is false.

**Fix (as proposed by the auditor).** Restore the ΔP_C column, or at least show it when any |dP| > 0.05 pts. Rewrite the footnote: the price gap is the same in every row, but the closing probability still moves with the buyer pool (thin-pool factor) and with deal size (base rate). Remove 'ΔP_C' from the line-1887 note if the column stays hidden.

## 4. The Data tab says two businesses with identical financials and very different owner dependence get the same closing probability; at the same ask they do not

- **Key:** `closing:datatab:pc-quality-independence-claim-false-at-fixed-ask`
- **Severity:** low
- **Where:** index.html Data tab provenance list, 'Probability of closing' item (~lines 5270-5276): 'This does not condition on business quality. Two businesses with identical financials and wildly different owner dependence receive the same number'

**Reproduction.** Framework example (EX), own 0.95 against own 0.10 (everything else identical). Ask $4.5M: own .95 gives V $3.81M, gap +18.1%, P_C 0.5697; own .10 gives V $4.51M, gap -0.3%, P_C 0.6769. Ask $5.5M: 0.3997 against 0.5248. They are equal only when the ask is at or below both values (ask $3.22M: 0.6769 both).

**Why it is wrong.** The gap is measured against the quality-adjusted value V = Vbase x qFactor. At any ask above the weaker business's V, owner dependence (and every other quality input) moves P_C through the gap. Independence holds only at a fair ask (ask/V fixed), which is what the code and the tests check (verified: spread below 2e-16 across 960 quality draws at ask = V). The text claims more than that. The same item also omits the size interpolation of the base and the thin-pool factor.

**Fix (as proposed by the auditor).** Reword: 'At the same ask relative to its model value, the closing probability does not depend on quality. At the same dollar ask, a better business has a smaller price gap and so closes more often.' Mention the size-interpolated base and the thin-pool factor.

## 5. The closing-probability equations do not match the code beyond a 100% gap or at the 2% floor, and the floor freezes P_C and EVp again from about 28x value

- **Key:** `closing:eq_p-eq_ps:formula-omits-tail-floor`
- **Severity:** low
- **Where:** index.html render(): eq_p ('P_C = b_recent(1 - 0.45 F_gap(g))'), eq_ps, the sensitivity 'pinned at its floor' note; fitClose/model clamp(...,.02,.95)

**Reproduction.** Framework example. At ask 3 x V: gap +200%, eq_ps prints a gap penalty of 0.509, which the eq_p formula 1 - 0.45F (F <= 1) cannot produce; eq_p also omits the thin-pool factor and the base's size interpolation. At ask 30 x V: base x (1-pen) = 0.0155, but eq_ps boxes P_C = 2.0%. From about 28 x V upward, P_C = 0.0200, Vmean/V = 1.1528 and EVp = $94,238 are identical at 30x, 50x, 100x, 1,000x and 10,000x; only tMed moves. The sensitivity note there says 'the price-gap penalty is already at its maximum', but the penalty has no maximum (it tends to 1); the 2% clamp is what binds.

**Why it is wrong.** Audit fix #9 set the rule that each panel shows the formula that produces the number beneath it. The gap tail (1-0.55e^{-K(g-100)}) and the thin-pool factor were added later and the general equation was not updated, so the instance line contradicts it. The 0.02 clamp also brings back, from about 28x, the flat region the tail was added to remove ('asks from 2x to $100B had the same closing probability'), and the floor note describes the cause wrongly.

**Fix (as proposed by the auditor).** Typeset the piecewise penalty in eq_p (0.45 F_gap(g) up to 100%, then 1-0.55 e^{-k(g-100)}), add the thin-pool factor and the size-interpolated base, and show 'max(2%, ...)' in eq_ps when the clamp binds. Change the floor note to 'pinned at the 2% floor'. Either let P_C keep decaying below 2% or state that the floor is a deliberate judgment.

## 6. Delay cost is shown as λ_T·E[T] but is computed on the median, which under the log-logistic curve is 22–31% below E[T], by an amount that depends on size

- **Key:** `timing:utility:median-used-as-E[T]`
- **Severity:** medium
- **Where:** index.html bestRatio U (line ~3240: -lamT*r.tMed), optNote U and nb (~3285, ~3297), optimize recV.U/recU.U (~3432/3437), eq_u/eq_us (~4375-4380: label -λ_T(E[T]+T_exec), value Math.round(best.U.t+best.U.days) with t = tMed), optimizer 'Total days' tile

**Reproduction.** node: const r=model({...ex,ask:V}) for the framework example (medical, $1.45M SDE) gives tMed 248.2 d and betaT 2.64. The log-logistic mean is E[T] = tMed·(π/β)/sin(π/β) = 318.2 d (×1.282). Under $500K, β is 2.20 and the factor is ×1.443 (tMed 198 → E[T] 286). Before this round the Weibull k=1.42 gave ×1.178 at every size. Even the mean restricted to the drawn 540 days is 238 d (β 2.20, tMed 198) and 278 d (β 2.64, tMed 248), so E[T] exceeds the median however the tail is cut. On the default page (Playwright) eq_us reads '− $900 · 403' under the label λ_T(E[T]+T_exec). 403 is tMed (≈250) + T_exec, so true E[T]+T_exec ≈ 474 and the delay term is understated by about $64k. Walk-away ask from a 0.0025 grid scan of the same U with tMed replaced by E[T] (θ .75, $4,000/day): home $100k SDE 1.080 → 1.060; prof $150k 1.105 → 1.090; prof $400k 1.130 → 1.125. At θ 0.5, $4,000/day, home $100k: 1.070 → 1.0525. The framework example barely moves (1.145 → 1.1425).

**Why it is wrong.** With a linear cost per day the expected delay cost is λ·E[T], and the displayed equation says exactly that. The code plugs in the median instead. The log-logistic is right-skewed, so its median sits well below its mean, and the gap depends on β, which now depends on deal size. As a result the delay cost is understated by 28–44% (mean over median), and the time cost of overpricing (d tMed/d ask) is understated by the same factor. That biases the walk-away ask upward, and more for small businesses (β 2.20) than for large ones. The printed number is labelled E[T] but is a median. The switch from Weibull to log-logistic this round widened this gap from 1.18 to 1.28–1.44 and made it depend on size.

**Fix (as proposed by the auditor).** Either: (a) charge the expected time: E[T] = tMed·(π/β)/sin(π/β), or a mean restricted to the histograms' top bin if the tail is not trusted. Store it as out.tMean and use it in bestRatio's U, optNote's U and nb, optimize's recV/recU, eq_us and the 'Total days' tile. Then re-pin the Data-tab walk-away-ask figures and the patient-seller flip points. Or (b) keep the median as a labelled judgment: relabel eq_u as λ_T(t_med + T_exec) and say in the Data tab that charging the median understates a per-day cost by 28% ($500K up) to 44% (under $500K).

## 7. The time-curve SVG's accessible label calls a curve that is conditional on closing the probability of closing

- **Key:** `timing:drawCurve:aria-label-unconditional`
- **Severity:** low
- **Where:** index.html line 1814: <svg id="tcurve" ... aria-label="Cumulative probability of closing over time">

**Reproduction.** On the default page (Playwright), tcurve's aria-label is 'Cumulative probability of closing over time'. The curve drawn under it is r.F(t) = 1/(1+(t/tMed)^-β). It reaches F(540) ≈ 0.89 and tends to 1, while r.PC = 0.62 (the in-SVG caption says '62% of listings close'). A screen-reader user is told the listing's chance of closing passes 89%.

**Why it is wrong.** F(t) is the share of deals that close which have closed by day t, not the unconditional chance that this listing has closed by day t. The unconditional figure is P_C·F(t), which is at most 62% here. The visible caption was fixed earlier (AUDIT: 'conditional on closing'), but the accessible name still states the unconditional reading.

**Fix (as proposed by the auditor).** Set aria-label to something like 'Share of closing deals closed by day t (conditional on closing)', or update it in drawCurve to include P_C, e.g. '…; X% of listings close'.

## 8. The state dropdown omits 11 states, DC and 3 territories that have fitted effects shipped and counted

- **Key:** `risk:ui:state-dropdown-missing-jurisdictions`
- **Severity:** low
- **Where:** index.html STNAMES (40 entries) feeding the i_st select and OMNI_STLAB; Data tab 'state, ${Object.keys(R.state_effects).length}' = 54 and '54 states and territories'; nFit counts all 54

**Reproduction.** Comparing the STNAMES keys with MODELS.risk.state_effects shows 14 keys with no option: AK, DC, DE, GU, HI, ND, NM, PR, RI, SD, VI, VT, WV, WY. In the browser i_st has 41 options (National average + 40 states). At the framework example these states would change the 10-year risk: PR -0.26 pts (x0.918), DE -0.22, AK -0.21, VT -0.19, SD +0.15, WY +0.12, DC +0.12, WV -0.10, ND -0.09. A deal in any of them can only be priced as 'National average'. tests/fuzz.test.js exercises all 54 through the model, but the UI cannot reach them.

**Why it is wrong.** The Data tab presents 54 fitted state and territory effects and counts them as fitted parameters the console uses, but 14 cannot be selected. Users in those jurisdictions silently get the national figure, and the label list is incomplete.

**Fix (as proposed by the auditor).** Add the missing names to STNAMES (Alaska, Delaware, District of Columbia, Hawaii, North Dakota, New Mexico, Rhode Island, South Dakota, Vermont, West Virginia, Wyoming, Puerto Rico, Guam, U.S. Virgin Islands). Alternatively, count and describe only the selectable ones.

## 9. The business score and its band caption treat the number of buyers contacted as business quality, so a top-quartile business is called 'below most peers' or 'bottom decile'

- **Key:** `scores:render:business-score-counts-outreach`
- **Severity:** medium
- **Where:** index.html render() hero block (about lines 3970-3999): rq=model({...s,ask:askOpt}) keeps s.buyers; r.scoreQ=Math.max(omniScore(rq),r.score); band(r.scoreQ) writes o_cap. The reference peers in refDistAt/mkT are fixed at buyers:I.buyers.

**Reproduction.** node: const A=require('/home/user/last-minute/tests/load.js'); ex={ind:'medical',rev:6e6,ern:1.45e6,ask:3.24e6,grw:.14,gm:.64,rec:.72,cc:.18,ret:.91,plt:.38,own:.72,mgt:.36,fin:.74,yrs:6,st:null,franchise:false} (the reset example). For buyers b: s={...ex,buyers:b}; V=A.model({...s,ask:1}).V; rq=A.model({...s,ask:V*A.bestRatio(s,0,0)}); A.omniScore(rq). Business score by buyers: 65 -> 79, 50 -> 79, 40 -> 67, 30 -> 47, 25 -> 33, 20 -> 13, 10 -> 1. rq.qPct stays 0.79 every time and the ask is the proceeds optimum every time. A perfectly median profile (every dimension at its peer median, medical at $1.45M SDE, typical pool 50) gets business score 50 at 50 buyers, 32 at 35, 7 at 25 and 1 at 20 (rest: 15 at 25 buyers; saas: 13 at 20). Browser (Playwright, reset state, i_buy set to 20, then IN.ask=STATE.r.askOpt): the hero shows 'Quality position 79th percentile', Business score 13 and the caption 'The business is below most peers of its size, and the gaps will be priced in, and the ask is close to optimal: within 0.0% of the best expected proceeds.' At 10 buyers the caption reads 'in the bottom decile for its size: buyers will price the gaps hard'. A deeper pool adds only up to +5 (median at 600 buyers: 55), so the effect is almost entirely a penalty.

**Why it is wrong.** The business score is defined, in the code and on the card, as the profile priced at its optimal ask so that it 'measures the business alone', separate from the seller's process decisions. 'Qualified buyers to be contacted' is a marketing decision of the same kind as the ask: the optimiser even sells it as an intervention ('Widen the qualified buyer outreach', x2.2 buyers, $18k, 45 days). The thin-pool factor is pool-only by construction and does not depend on quality. Yet the business score keeps the subject's pool while every peer sits at the typical pool, so outreach moves the business score by up to 78 points. The band caption then blames the business's quality ('the gaps will be priced in') right beside a quality percentile of 79, and the caption never mentions the pool. AUDIT.md settled the thin-pool effect on the Omni score (at your ask and your process), but not on the business score or the quality caption.

**Fix (as proposed by the auditor).** Price the business score at the optimal ask AND at least a typical pool: sB={...s,buyers:Math.max(s.buyers,IND[s.ind].buyers||50)}; rhoB=bestRatio(sB,0,0); rq=model({...sB,ask:model({...sB,ask:1}).V*rhoB}). The invariant business >= Omni still holds, because thinF and compPrem never fall as buyers rise. Make the caption split what the Omni score loses into the ask's share and the pool's share. Compute an intermediate model({...s,ask:askOpt}) and say e.g. 'contacting N buyers against a typical M costs X% of expected proceeds and K points'. Alternatively, read the band from r.qPct. Add a test: a median business at half the typical pool keeps business score 50.

## 10. Model value is labelled a 'financial-buyer baseline', yet all three financial buyers plot above it as 'strategic premium'

- **Key:** `buyers:labels:financial-baseline`
- **Severity:** low
- **Where:** index.html drawStars (the reference line 'model value — above this line is strategic premium', around line 3745); eq_bs '+X over the financial baseline' (line 4226); the BUYERS comment 'mf: multiple factor relative to the financial-buyer baseline'; the lede 'what it could justify paying'

**Reproduction.** Framework example: V = $4.09M. PE platform Vj $4.15M, family office $4.12M and PE add-on $4.26M are all financial buyers, yet all three sit above the line labelled 'above this line is strategic premium'. eq_bs reads 'pays most: Direct strategic competitor -> $5.19M (+$1.10M, +26.8% over the financial baseline)'. The financial archetypes have mf 1.06/1.02/1.12, so none of them is the mf = 1 baseline. Vj also includes only phi = 0.38 of synergy, while the lede says 'what it could justify paying'. The SVG aria-label says 'by strategic fit and expected value', but the y-axis is Vj.

**Why it is wrong.** V is the BIZCOMPS closed-sale value, where most buyers are individuals in small deals. It is not a financial-buyer price. Calling the premium over it 'over the financial baseline' and 'strategic premium' misattributes it, and the chart contradicts its own label. Vj is the price after the seller's synergy share, not what the buyer could justify (standalone value + S).

**Fix (as proposed by the auditor).** Relabel as 'premium over model value' / 'above model value', change the BUYERS comment, call Vj 'price this buyer would pay' (or show standalone + S as its justifiable value), and fix the aria-label.

## 11. The utility card calls an identical set of changes "a different programme" and says it costs less time and spend, when it costs the same and takes longer

- **Key:** `decisions:optout-card:same-programme-called-different`
- **Severity:** medium
- **Where:** index.html render(), optimizer cards (sameSet / dProc subtitle, about lines 4360-4369)

**Reproduction.** node -e with tests/load.js at the framework defaults (medical, rev 6e6, ern 1.45e6, ask 3.24e6, buyers 65, budget 1e5, lamT 900, theta .75; s.optRho=bestRatio(s,.75,900)=1.148, s.rhoSell=bestRatio(s,0,0)=1.101), then optimize(s,model(s),1e5,900,.75). best.V.keys and best.U.keys are both [reprice,qoe,margin,outreach] at the same $87k cost. Total days are 402 (V) and 403 (U), and proceeds are $2.894M and $2.779M. Because uRho.toFixed(2) is not rhoSell.toFixed(2), sameSet is false. Playwright on the default page shows: "A different programme: it gives up $115k of expected proceeds in exchange for less elapsed time and spend, or the 75% of value retained if the process fails." On a 192-case grid (6 industries x 4 sizes x theta .3/.5/.75/.9 x lamT 0/900), 142 cases have identical keys with only the reprice ratio differing. In all 142 the card claims less time and spend, while spend is equal and elapsed time is equal or longer.

**Why it is wrong.** The fourth audit added the ratio check to sameSet so the cards would stop saying "the same programme" when they reprice to different ratios. That routes the common case (same interventions, higher ask) into the branch written for a different set of interventions. Its text is false here. The programme is the same. Spend is identical. A higher ask lengthens the time to close through timeMult, so elapsed time is longer, not shorter. The only real trade is closing probability (65.8% to 61.5%) for a higher price if it closes, and that pays only through theta. This text appears at the console's own defaults.

**Fix (as proposed by the auditor).** Split the branch. When the key sets match and only the reprice ratio differs, say for example "The same changes, repriced to 1.15x instead of 1.10x: it gives up $115k of expected proceeds and 4.3 pts of closing probability for a higher price if it closes (about N days longer). It pays only through the 75% of value kept if the process fails." When the key sets differ, compute whether best.U really has lower spend (c) and lower total days (t+days), and mention only what is true. Add a test pinning the default-state subtitle.

## 12. The intervention table says the closing probability is the same in every row, but outreach on a thin pool moves it by up to 20 points

- **Key:** `decisions:interventionTable:footnote-pc-same-every-row`
- **Severity:** low
- **Where:** index.html render(), #intbl footnote (about line 4321), and the removed ΔP_C column (AUDIT fourth audit, Decisions)

**Reproduction.** Take the defaults with buyers 25 (typical pool 50) and run interventionTable(s,model(s)). The outreach row has dP = +15.11 pts and dE = +$615k: P_C goes from 50.4% repriced to 65.5%, because thinF goes from 0.77 to 1. At buyers 15 it is +20.27 pts; at 35, +6.86 pts. Rows that change earnings also move P_C through the size-based base close rate. At the default 65 buyers: margin +0.25, gm -0.28, growth +0.17 pts. Playwright at buyers 25 shows outreach first, at +$615k and 3316% ROI. The footnote still reads "Each change is measured on top of a reprice to 1.10x its new value, so the price gap, and with it the closing probability, is the same in every row".

**Why it is wrong.** The ΔP_C column was removed, and the footnote written, on the premise that repricing every row makes P_C identical by construction. That premise broke when the thin-pool factor (thinF, now capOne at the ENG_SHARE scale) and the size-interpolated broker/intermediated base were added: P_C now depends on the buyer pool and on Vbase, not only on the price gap. The table hides the mechanism behind the largest row on thin pools and states something false about it.

**Fix (as proposed by the auditor).** Restore a ΔP_C column (r1.PC - rb.PC is already computed as dP). Reword the footnote: the price gap is the same in every row, so the closing probability moves only through the buyer pool (outreach below a typical pool) and through deal size. Add a test that the outreach row's dP is positive below the typical pool.

## 13. The utility charges the cost of delay on the median time to close but prints it as E[T], understating the expected delay cost by 28-43%

- **Key:** `decisions:utility-eq:median-labelled-ET`
- **Severity:** low
- **Where:** bestRatio U(), optNote U(), optimize recV.U/recU.U (lamT*r.tMed); eq_u / eq_us in render() (about lines 4375-4380)

**Reproduction.** At the defaults, model(s) gives betaT 2.64 and tMed 248.2 days. The log-logistic mean is tMed*(pi/beta)/sin(pi/beta) = 318.2 days (numeric integration of S(t) agrees), a ratio of 1.282. For a $150k-SDE business, beta is 2.23 and the ratio is 1.428 (203.9 vs 291.1 days at ask 4.5e5). eq_u typesets -lambda_T(E[T]+T_exec), but eq_us substitutes Math.round(best.U.t+best.U.days) = 403, where t = tMed. With E[T] the delay term would be about 900 x (323.9+150) instead of 900 x 403, so the boxed U ($3.62M) overstates by about $64k, or 1.4% of V. The walk-away ask barely moves (1.148 either way; at theta 0, lamT 4000 it goes from 1.100 to 1.099).

**Why it is wrong.** A linear per-day cost of delay has expected value lambda*E[T]. The median of a right-skewed log-logistic is well below its mean, so the objective under-charges delay, and the equation panel names a quantity the code does not compute. That is the class of mismatch AUDIT item 9 fixed elsewhere ("Each panel now shows the formula that produces the number beneath it"). Decisions are hardly affected because T_ELAST is small. The U level, and the comparison of programmes whose times differ through deal size, are biased.

**Fix (as proposed by the auditor).** Either charge the mean: replace r.tMed in the utility (bestRatio, optNote, optimize) with r.tMed*(PI/beta)/sin(PI/beta), beta = r.betaT, which is always above 2 here. Or keep the median and typeset it honestly as -lambda_T(t_med + T_exec), with a note that the median is used. Re-pin the theta-flip and near-tie numbers in the comments and tests if the code changes.

## 14. The lower-ask optNote presents the net utility gain as the dollar value of the time saved

- **Key:** `decisions:optNote:lower-branch-net-gain-as-time-value`
- **Severity:** low
- **Where:** index.html optNote(), kind "lower" text (about lines 3334-3341)

**Reproduction.** Run prep({theta:0,lamT:4000,rev:8e5,ern:1.5e5,ask:4.5e5}): rhoSell 1.1007, optRho 1.0720, and optNote gives "Listing at $367k gives up $868 of expected proceeds, but it is 0.7 pts more likely to close and closes slightly sooner, which at $4k a day is worth $882 to this owner". The days saved are rS.tMed-rK.tMed = 0.438, and 0.438 x $4,000 = $1,750 of time value. $882 is the net gain U(rKeep)-U(rSell) = $1,750 - $868.

**Why it is wrong.** The "which at $X a day is worth $gain" clause attaches gain to the faster close, so a reader nets it against the $868 given up and concludes the change is worth about $14. It is worth $882. The "higher" branch words the same quantity correctly ("worth only $gain more to this owner after the cost of delay"). The dollar amounts are small, because this branch fires mainly for small businesses at high lamT.

**Fix (as proposed by the auditor).** State the time value and the net separately: "...closes about N days sooner, worth $1,750 at $4k a day. Net of the proceeds given up, that is $882 to this owner." Here lambda*(rSell.tMed-rKeep.tMed) is the time value and gain is the net. Or say "on balance this is worth $gain more to this owner".

## 15. Second optimiser card says the walk-away programme saves time and spend when it saves neither

- **Key:** `optimizer:optout-card-U:false-time-and-spend-claim`
- **Severity:** medium
- **Where:** index.html:4364-4370 (render(), $("optout") card for best.U; sameSet/dProc text)

**Reproduction.** Framework default (medical, rev $6M, SDE $1.45M, ask $3.24M, 65 buyers, budget $100k, $900/day, theta 75%). optimize(s,r,1e5,900,.75) gives best.V = [reprice 1.10x, qoe, margin, outreach], cost $87,000, exec 150 d, tMed 251.6 d (total 402 d), proceeds $2.894M, P_C 65.8%. best.U = the same four changes with the reprice at 1.15x, cost $87,000, exec 150 d, tMed 252.7 d (total 403 d), proceeds $2.779M, P_C 61.5%. The card prints: "A different programme: it gives up $115k of expected proceeds in exchange for less elapsed time and spend, or the 75% of value retained if the process fails." Spend is identical ($87k vs $87k) and elapsed time is one day LONGER (403 vs 402).

**Why it is wrong.** The text hard-codes "less elapsed time and spend" whenever dProc<0 and never compares best.U.c/best.U.days+t with best.V. When the two programmes differ only in the reprice ratio (the common case, and the default), the U programme has the same spend and, because timeMult stretches tMed above value, a longer time. What it actually trades is a lower closing probability for a higher price if it closes and more retained value if it fails. The dProc>0 branch ("at a higher cost") makes the same untested claim.

**Fix (as proposed by the auditor).** Describe the actual differences. Compare cost (best.U.c vs best.V.c), total days (t+days) and P_C, and name only the ones that move in the stated direction. When the keys are equal and only the reprice ratio differs, say "the same changes, repriced to 1.15x instead of 1.10x: X pts less likely to close for a larger price if it does, plus theta of value retained if it fails".

## 16. Closing probability is still badged and described as conditioning on size and gap only, but the thin-pool factor scales it by buyers contacted

- **Key:** `presentation:closing-prob:thin-pool-not-in-badge-or-captions`
- **Severity:** medium
- **Where:** index.html:1742 (Chance of closing badge 'aggregate', no title); 1790 (§5-7 lede 'conditions on deal size and asking gap only'); 4175 eq_p (P_C=b_recent(1-0.45F_gap) with no thin-pool term); 4630 (Data tab Model I lede 'conditions on the only two things the tables are cut by: deal size and the gap'); 5332-5336 footer ('closing probability and timing are market aggregates conditioning on deal size and price gap alone'); 1743 Expected-proceeds tooltip ('Aggregate closing probability ...')

**Reproduction.** In the browser at the framework default, set 'Qualified buyers' to 25 (typical pool 50). The tile reads 'Chance of closing [aggregate] 52%'. At 65 buyers it reads 68%. model(): thinF 0.769, P_C 0.521 vs 0.677. eq_ps does show '× 0.769 thin pool = 52.1%', but eq_p directly above it still typesets P_C = b_recent·(1 − 0.45·F_gap(g)), and the lede beneath the tile says it 'conditions on deal size and asking gap only'.

**Why it is wrong.** Below a typical pool, P_C = base × (1−pen) × capOne(Poisson ratio). The scale is calibrated (ENG_SHARE). The Poisson shape, THIN_W and the typical pool IND.buyers are labelled judgment. So the number now conditions on buyers contacted and carries judgment inputs, and here it moves 16 points. The time tile already got the matching treatment for T_ELAST: its badge switches to 'aggregate × judgment' with an explanatory note. The P_C tile, its equation and four captions were not updated.

**Fix (as proposed by the auditor).** When thinF<1, switch the o_pc badge to 'aggregate × calibrated/judgment', with a title naming the thin-pool factor, as o_t_pv does. Add the thin-pool term to eq_p (× capOne((1−e^{−n_pool})/(1−e^{−n_typ}))). Reword the §5-7 lede, the Data-tab Model I lede, the footer and the Expected-proceeds tooltip to say: deal size, gap and, below a typical pool, the number of buyers contacted.

## 17. Intervention table footnote says the closing probability is the same in every row, and the caption cites a ΔP_C column that does not exist

- **Key:** `presentation:intervention-table:closing-prob-not-constant`
- **Severity:** medium
- **Where:** index.html:4321 (intbl footnote row); 1887 (static caption 'ΔE[proceeds], ΔP_C and ROI are measured on top of a free reprice')

**Reproduction.** interventionTable() at the framework default with buyers=25: the outreach row has dP = +15.11 pts (P_C 50.4% → 65.5% via thinF), ΔE[proceeds] +$615k, ROI 3316%. The table still ends: 'Each change is measured on top of a reprice to 1.10× its new value, so the price gap, and with it the closing probability, is the same in every row'. Even at the default 65 buyers the margin, GM and growth rows move P_C by +0.25, −0.28 and +0.17 pts, through the size-interpolated base rate on Vbase. The ΔP_C column was removed (AUDIT 4th round) on the premise that it is identically zero, but the caption still names it.

**Why it is wrong.** The premise behind both texts (repricing equalises the gap, so P_C is constant) stopped holding when two later changes landed: the thin-pool factor, and the base rate interpolated in ln(Vbase) from $1M to $5M. For outreach under a thin pool, almost all of the ΔE[proceeds] is a closing-probability effect that the table now hides and explicitly denies.

**Fix (as proposed by the auditor).** Restore a ΔP_C column, which the interventionTable already returns as dP, or at least drop the 'same in every row' clause. Say that the gap is equalised but P_C still moves through pool depth (outreach) and through the size band (earnings changes). Remove 'ΔP_C' from the static caption if no column shows it.

## 18. optNote 'lower' branch labels the NET utility gain as the value of closing sooner, which reads as a net loss

- **Key:** `optimizer:optNote-lower:net-gain-labelled-as-delay-value`
- **Severity:** medium
- **Where:** index.html:3334-3340 (optNote, kind 'lower')

**Reproduction.** Framework example with ern $400k, rev $1.667M, theta 0, lamT $4,000/day: rhoSell 1.101, optRho 1.090. Expected proceeds change −$459, delay saving λ·ΔtMed = +$800, net U gain +$341. The note reads: "Listing at $1.05M gives up $459 of expected proceeds, but it is 0.3 pts more likely to close and closes slightly sooner, which at $4k a day is worth $341 to this owner". With theta .2, $4k/day, ern $150k: gives up $573, delay worth $1,492, retained term −$395, net +$524, and the note prints 'worth $524'.

**Why it is wrong.** `gain` is U(rKeep)−U(rSell), and it already nets out the proceeds given up and the change in retained value. The sentence attaches it to 'closes sooner, which at $X a day is worth ...'. A reader subtracts again ($341 − $459 < 0) and concludes that the recommended lower ask is worse, which contradicts the recommendation. The true value of the speed-up is $800.

**Fix (as proposed by the auditor).** Print the delay value λ·(rSell.tMed − rKeep.tMed) after 'which at $X a day is worth'. Then state the net separately ('a net gain of $gain to this owner after the proceeds given up'), or rephrase as 'on balance worth $gain more to this owner'.

## 19. Utility equation charges delay on E[T] but the code and the substituted figure use the median time to close

- **Key:** `equation:eq_u:median-labelled-expected-time`
- **Severity:** medium
- **Where:** index.html:4375-4381 (eq_u, eq_us); 3240 bestRatio U, 3285 optNote U, 3431-3437 optimize use r.tMed

**Reproduction.** Framework default: eq_us prints '−$900·403', where 403 = best.U.t (tMed 252.7 d) + 150 exec days. eq_u labels that term λ_T(E[T]+T_exec). The curve is log-logistic with β = 2.64, so E[T] = t_med·(π/β)/sin(π/β) = 1.2818 × 252.7 = 323.9 d (numerical integration of tQ: 323.9). On the printed definition the delay charge is $900 × 474 = $426.6k, not the $362.7k used, a $64k gap. That is larger than the $24k utility margin between the two listing asks reported in the optNote.

**Why it is wrong.** For a right-skewed time-to-close the mean and median differ by 28%. The panel names a quantity the model never computes, so a reader who checks the arithmetic with an expected time gets a different U. The listing and optimiser decisions are also sensitive to the choice.

**Fix (as proposed by the auditor).** Relabel the term t_med (the median time to close) in eq_u and eq_us, and say 'median' in the U card. Alternatively, charge the mean tMed·(π/β)/sin(π/β) consistently in bestRatio, optNote and optimize, then re-pin the Data-tab walk-away figures.

## 20. Data tab quotes the pre-shrinkage SDE margin range 18–35%; the shipped fitted medians are 20–30%

- **Key:** `datatab:fitted-public:sde-margin-range-stale`
- **Severity:** low
- **Where:** index.html:4998 (Fitted from public data, 'Typical SDE margin' row, hard-coded '18&ndash;35%')

**Reproduction.** typMargin(k, 2e5) over all 16 industries (plus 'other') = exp(ln_at_ref) = 19.8% (dist) to 29.9% (msp). The row prints 'fitted medians 18–35% at $200k SDE'. The 18.3–35.0% range is exp(ln_at_ref) from commit 7c51d98, before be22821 shrank industry margins by n/(n+50). AUDIT.md's own table gives '20–30% at $200k SDE (shrunk toward the pooled level)'.

**Why it is wrong.** The slope (+0.075) and sd (0.59) in the same cell are read live, but the range is a literal left over from the unshrunk fit. It overstates the spread of industry margins the model actually uses by about 70%.

**Fix (as proposed by the auditor).** Compute the range live: Math.min/max over Object.keys(IND) of typMargin(k,2e5), formatted to whole percent. That gives '20–30%'.

## 21. Data-tab headline says 14 aggregate parameters while the Aggregate section says 17; the fitted tally also counts the tail factor the page labels judgment

- **Key:** `datatab:tally:aggregate-count-mismatch`
- **Severity:** low
- **Where:** index.html:4452 (tally literal 14); 4624 (Aggregate heading literal '17 parameters'); 4435 (nFit '+ 3 /* ... tail factor */')

**Reproduction.** The Data tab renders '14 read from published market aggregates' at the top and 'Aggregate 17 parameters' in the section heading. git log -S shows the heading went from 16 to 17 in be22821, after the prime rate, Census and BLS aggregates were added ('Three more published aggregates feed ...'). The headline literal has been 14 since the first commit. Separately, nFit = 481 includes R.tail_factor through the '+3', yet the same tab calls ×1.20 'a judgment' (Model V trap 4 and the Fitted-from-public-data risk row), and nJudg (297) does not include it.

**Why it is wrong.** Two hard-coded counts of the same thing disagree on the same page, and one parameter is counted as estimated from outcomes while it is labelled judgment. The badge tallies are presented as 'generated from the live model constants, so they cannot drift'.

**Fix (as proposed by the auditor).** Use one constant (or a computed count) for both the headline and the section heading. Either move tail_factor from nFit's '+3' to nJudg, or stop calling it judgment in the text. Rephrase the '+3' comment to match.

## 22. Self-audit row 'judgment-stack net adjustment for a business at its peer medians' reads 'off' because its profile is not at the peer median margin

- **Key:** `selfaudit:judgment-stack-row:tests-wrong-profile`
- **Severity:** low
- **Where:** index.html:5208-5215 (renderCalib, ms=at("prof",158950,703000) used for the first row)

**Reproduction.** The live Data tab shows '-0.033 vs 0.000 ± 0.03, off'. Decomposition of ms.d: em = −0.0295, tail = −0.0035, every other delta 0. Revenue 703,000 gives a 22.6% margin against the fitted peer median typMargin('prof',158950) = 25.9% (em z = −0.23). With rev = ern/typMargin (a business actually at its peer medians), dsum = −0.0035, which is in range. AUDIT round 3 recorded only two honest 'off' rows (2.35x and 6.77x), so this third one appeared when SDE margins were fitted.

**Why it is wrong.** The row claims to test centring at the peer medians, but it feeds the BizBuySell median revenue. Since the margin norms became fitted, that revenue puts the business 0.23 sd below its margin norm, so the check fails for a reason unrelated to its label.

**Fix (as proposed by the auditor).** Evaluate this row on prof('prof',158950) without the revenue override, i.e. rev = ern/typMargin. Keep the 703k BizBuySell profile for the BizBuySell rows only.

## 23. '15 quarters (2020Q1–2023Q3 and 2025Q4)' names 16 quarters; 2022Q1 is not in the fit

- **Key:** `presentation:ttc:quarter-range-label`
- **Severity:** low
- **Where:** index.html:1809 (§9 lede), 4677 (Data tab Model III), 5025 (Fitted-from-public-data ttc row), 5288 (provenance list); fit/README.md ttc_shape row

**Reproduction.** 2020Q1–2023Q3 is 15 quarters on its own (4+4+4+3), and adding 2025Q4 makes 16. fit/time_to_close_shape.py's docstring gives the actual set: '15 quarters (2020Q1-2021Q4, 2022Q2-2023Q3, 2025Q4)', so 2022Q1 is missing. MODELS.fitted.ttc_shape.n_quarters = 15.

**Why it is wrong.** The printed range and the printed count contradict each other, and the range claims a quarter the fit never used.

**Fix (as proposed by the auditor).** Write '15 quarters (2020Q1–2021Q4, 2022Q2–2023Q3 and 2025Q4)' everywhere, including ttc_shape.source and the README.

## 24. Value equation is typeset without units; taken literally in dollars it gives $0.73M instead of $3.28M

- **Key:** `equation:eq_v:units-missing`
- **Severity:** low
- **Where:** index.html:4155-4157 (eq_v); Data tab equation box at 4517-4526

**Reproduction.** Framework default (medical e_i = −0.0865): evaluating eq_v as printed with SDE = 1,450,000 and rev = 6,000,000 gives exp(lnP̂) = $729,752. The code (fitValue) uses ln(SDE/1000) and ln(rev/1000) and returns P̂ in thousands, so rawPoint = $3,277,007, which eq_vs prints as $3.28M. MODELS.value.target is 'ln(sale_price_thousands)', but neither panel says so.

**Why it is wrong.** The coefficients on ln SDE and ln rev sum to 0.783, not 1, so the intercept is unit-dependent. Without '$000' the displayed equation does not reproduce the boxed figure beneath it.

**Fix (as proposed by the auditor).** Typeset the variables in thousands, e.g. \ln\hat P_{\$000}, \ln(\text{SDE}/\$1\text{k}) and \ln(\text{rev}/\$1\text{k}), in eq_v and in the Data-tab equation, or add '(all $ in thousands)'.

## 25. eq_p bounds the gap penalty at 0.45, but beyond a 100% gap the code's tail drives it toward 1

- **Key:** `equation:eq_p:penalty-cap-vs-tail`
- **Severity:** low
- **Where:** index.html:4175 (eq_p '1−0.45 F_gap(g)'); 4686-4688 Data tab ('The penalty on the console is this distribution's cumulative')

**Reproduction.** gapPenalty(150) = 0.480, (200) = 0.509, (300) = 0.562. At the framework example with the ask at 2.5x value (the slider's top), eq_ps prints '(1 − 0.480 gap penalty)', while eq_p directly above it states the penalty as 0.45·F_gap with F a CDF ≤ 1.

**Why it is wrong.** Since the 4th audit, a smooth exponential tail, 1−(1−PEN_MAX)e^{−k(g−100)}, applies past the last Pepperdine bucket. The general formula and the Data-tab description were not updated, so within the slider's own range the substituted number contradicts the stated formula.

**Fix (as proposed by the auditor).** Add the tail case to eq_p (penalty = 1−0.55·e^{−k(g−100)} for g>100%, with k printed) and mention it in the Data-tab kill-zone note.

# Round 1 (verified at commit a6d235c)

Round 1 had 51 findings. Twenty were raised against 7cac297 before the round-0 batch. The other 31 came from four new auditors, who covered decisions, presentation, on-screen numbers against the model, and Data-tab claims against the code. Two verifiers checked every finding against a frozen copy of a6d235c: one reproduced it independently, the other tried to refute it. A finding is confirmed only if it reproduced and was not refuted. **34 were confirmed; 17 were rejected.**

## Confirmed

| # | Severity | Key | Title |
|---|---|---|---|
| R1-1 | medium | `closing:provenance:pen-max-unlabelled-judgment-sets-walkaway` | PEN_MAX = 0.45 (and the $1M-$5M channel ramp) set the reported 'aggregate' closing probability, are missing from both judgment ledgers, and decide the default patient-seller answer |
| R1-2 | medium | `price:scen:outcome-percentiles-conditional-on-close-unlabelled` | The 'Outcome distribution' scenarios are percentiles of the price if the deal closes, but they are labelled as outcome percentiles and leave out the no-sale outcome |
| R1-3 | low | `price:hero:model-value-badged-fitted-despite-judgment-quality-factor` | The 'Model value' and 'Expected multiple' tiles always carry a plain 'fitted' badge, though up to −27% / +32% of the number is the judgment quality position |
| R1-4 | medium | `buyers:ev:vj-priced-above-ask-ceiling` | Buyer EV, 'pursue first' and 'pays most' price each buyer at its full V_j, above the ask that caps every realised price |
| R1-5 | low | `buyers:pcj:gap-read-against-model-value-not-buyer-value` | Buyer-specific close probability ignores how the ask compares with that buyer's own value |
| R1-6 | medium | `risk:fitrisk:sba-cap-silently-binds-large-deals` | Above about $5.9M of model value the risk tile shows the risk of a capped $5M SBA note, without saying so |
| R1-7 | low | `risk:datatab:prime-claimed-to-feed-risk` | Data tab says the prime rate feeds the survival risk, but it cancels exactly and moves no figure |
| R1-8 | low | `risk:datatab:shipped-level-upper-part-false` | Data tab says the shipped 8-year level is in the upper part of its range, but it sits below the middle |
| R1-9 | low | `risk:datatab:corpus-auc-different-metric` | The state and 6-digit row quotes a CV AUC of 0.820 to 0.828, a different metric from the model's 0.718 out-of-sample AUC, with no label |
| R1-10 | medium | `decisions:optCardNote:retained-value-reason-read-off-pc-sign` | The shipped fix for #11/#15 is incomplete: optCardNote says the walk-away programme 'pays through the value retained if the process fails' when that term is lower under the walk-away programme (it reads only the sign of ΔP_C and ignores that V differs between programmes) |
| R1-11 | low | `decisions:optNote:coin-toss-threshold-scales-with-utility-level` | optNote's 'close to a coin toss' test is 1% of /U(rSell)/, a level that contains the whole delay charge λ·E[T]. The threshold shrinks to zero as the cost of delay rises and then grows again, so the caveat appears, disappears and reappears for a nearly identical gain |
| R1-12 | low | `decisions:sensflat:binding-ask-note-denies-quality-pass-through` | The sensitivity note says that, with the ask binding, improving the business does not raise what the listing collects, but the bar beside it shows up to 40% of the full pass-through (a quality response as large as the ask's own). The note also switches off at ask = V while the ask still binds |
| R1-13 | low | `decisions:interventionTable:net-days-on-median-not-mean` | The intervention table's 'Net days' still measures the time to close on the median after the E[T] fix, so the same change takes a different number of days in the table and in the optimiser's 'Expected days' tile (mean) |
| R1-14 | medium | `presentation:sensitivity:inverted-rows-shown-under-plain-derivative` | Sensitivity bars for customer concentration, channel concentration and the asking price show the effect of a cut, under headers and an equation that say ∂y/∂x, so their signs read backwards |
| R1-15 | medium | `presentation:rail:earnings-input-labelled-sde-or-ebitda-but-read-as-sde` | The earnings input is labelled 'SDE / EBITDA', but every formula reads it as SDE: entering EBITDA, as the label allows, undervalues by 26% and mislabels the EBITDA multiple |
| R1-16 | medium | `presentation:charts:svg-labels-3px-at-390` | At 390px every label in the buyer map and the time-to-close chart renders at 3.2–5.1px, and the 90/180/365-day closed shares appear nowhere else |
| R1-17 | low | `presentation:eq_cs:interval-labelled-fitted-residuals-is-ask-capped-price` | The confidence panel labels its 80% interval 'from fitted residuals', but it shows the ask-capped realised-price interval: 1.17× wide against the fitted band's 3.32×, and it moves with the ask |
| R1-18 | low | `presentation:hero-risk:fitted-badge-covers-judgment-tail-and-unexplained-ratio` | The survival-risk tile carries a plain 'fitted' badge with no tooltip, although 17% of its 10-year headline is the judgment tail factor, and its '(0.56×)' ratio is never explained on the Console |
| R1-19 | low | `presentation:eq_p:tail-rate-k-rounded-to-two-significant-figures` | eq_p prints the gap-tail rate as k=0.0011 when it is 0.0011356, so the formula on screen gives a different penalty and P_C from the boxed figures beneath it |
| R1-20 | low | `presentation:eq_v:general-form-terms-never-valued` | eq_v's h(SDE), m and e_i are never defined or given values on the Console, and eq_vs jumps from the general form straight to $3.28M; with h=0 and e_i=0 the printed coefficients give $1.46M |
| R1-21 | low | `presentation:multbl:stack-bounds-row-misstates-floor` | The multiple table's 'Bounds on the stack' row says the multiple is held to 0.42–1.85× base, but the floor that actually binds is an absolute 0.90× |
| R1-22 | low | `numbers:srcs:termination-risen-every-year-false` | The Console source note and the Data tab say Pepperdine termination 'has risen every year since the 2020–21 trough', but the shipped series falls from 28% to 27% in 2023 |
| R1-23 | low | `numbers:optnote:cost-of-delay-rounded-to-thousands` | The optimiser notes print the cost of delay through money(), so $1,450 a day reads as '$1k a day' (31% low) beside a dollar figure computed at $1,450 |
| R1-24 | low | `numbers:multbl:judgment-floor-0.90-unlabelled` | The multiple table's 'Bounds on the stack' row gives the multiple's bounds as 0.42–1.85× base, but the model also floors it at 0.90× absolute, so the displayed net and multiple do not reconcile |
| R1-25 | low | `numbers:qband:the-below-the-middle` | The quality-position note renders 'here, the below the middle' for a percentile between 15 and 38 |
| R1-26 | medium | `datatab:provenance:pc-conditions-only-on-gap` | Fix incomplete for presentation:closing-prob:thin-pool-not-in-badge-or-captions: the provenance key and the Data tab still say P_C conditions on the price gap (and size) only |
| R1-27 | low | `datatab:model3:mean-over-median-step-at-500k` | The Data tab says E[T] is 28% above the median from $500K of value and 44% below it, but β is interpolated between $250k and $707k, so the premium is 31–34% around $500K |
| R1-28 | low | `datatab:model2:hinge-credited-with-6digit-and-calibration-gains` | The hinge paragraph credits the size hinge with R² 0.7255 → 0.7546 and error 30.8% → 28.4%, but MODELS says the hinge gave 0.7399 / 30.1%; the same tab credits 0.7399 → 0.7546 to the 6-digit effects |
| R1-29 | low | `datatab:model1:termination-risen-every-year-false` | 'Termination ... has risen every year since' the 2020–21 trough is contradicted by the shipped series, which fell from 28% (2022) to 27% (2023) |
| R1-30 | low | `datatab:model5:size-gap-reverses-not-closes` | The Data tab says the loan-size hazard gap 'closes by year 6'; in the code it crosses zero at 5.4 years and reverses, so larger loans carry a higher charge-off hazard in years 6–8 |
| R1-31 | low | `datatab:tally:fitted-count-omits-and-mislabels` | The '480 estimated from transaction outcomes' tally leaves out fitted tables the model reads and the page badges fitted, and counts 39 parameters fitted to listings and survey aggregates |
| R1-32 | low | `datatab:tally:judgment-count-includes-industry-names` | The judgment tally and the IND inventory row count the 16 industry display names as hand-set parameters (IND × 10 fields includes 'n') |
| R1-33 | low | `datatab:selfaudit:fit-consistency-target-mislabelled` | The self-audit row calls BizBuySell's 90.5% 'the fit's own target', but FAN_S was set to the multi-source average, so the row reads 89.0% and passes only through its ±2.5-pt window |
| R1-34 | low | `datatab:crosscheck:dealstats-fitted-range-stale` | The cross-source check quotes a 'fitted' sector spread of 0.86–1.33. The shipped sector effects for the same 11 DealStats sectors span 0.86–1.43. |

### R1-1. PEN_MAX = 0.45 (and the $1M-$5M channel ramp) set the reported 'aggregate' closing probability, are missing from both judgment ledgers, and decide the default patient-seller answer

- **Key:** `closing:provenance:pen-max-unlabelled-judgment-sets-walkaway`  
- **Severity:** medium  
- **Where:** index.html: PEN_MAX (l.2311) and gapPenalty (l.2371); fitClose channel ramp (l.2387-2388); 'Chance of closing' tile badged 'aggregate' (l.1742) and pvkey 'Anchored to published market aggregates'; Data tab Model I note 'The penalty on the console is this distribution's cumulative' (l.4664); judgment inventory 'Bounds & constants' row (l.4917-4919, reaches only 'Price anchoring, competitive premium'); Still-judgement ledger (l.5105-5170, lists ALPHA/AMAX but not PEN_MAX); optNote range sentence (l.3285 ff.)

**Why it is wrong.** The reported P_C is presented as a Pepperdine aggregate: the badge says aggregate, the lede says 'a published base rate times a price-gap penalty', and the Data tab says the penalty 'is this distribution's cumulative'. But the size of the price response, PEN_MAX, is a judgment constant (AUDIT.md lists it with ALPHA as 'from the spec'). The broker-to-intermediated ramp is also judgment, because Pepperdine's tables are cut by channel, not by deal size. ALPHA from the same AUDIT sentence is disclosed in the Still-judgement ledger and PEN_MAX is not. PEN_MAX is load-bearing: a 0.02 change flips the default recommended walk-away ask between 1.15x and 1.50x, the same knife-edge the Data tab documents for FAN_S (flip near 0.90) and theta (0.77). The UI attributes that knife-edge only to price scatter.

**Verifier (reproduce).** Present at a6d235c. PEN_MAX is labelled judgment only in AUDIT.md ('Left as documented judgment ... the 0.45 maximum gap penalty come from the spec'). The console itself does not label it. The Data tab says the penalty is the Pepperdine cumulative, and the P_C tile is badged 'aggregate'. A 0.02 move in this unlabelled constant flips the default walk-away ask between 1.15x and the 1.5x cap. The optNote credits that tie only to price scatter (FAN_S). The ramp half of the finding is weaker but also real: the $1M–$5M interpolation is described ('interpolated in ln(value) from $1M to $5M') but never labelled judgment, and it moves the default P_C by -3.8/+2.0 pts without changing the walk-away ask. Medium severity is reasonable.

**Fix (as proposed).** Add PEN_MAX (0.45, spec judgment), the $1M-$5M channel ramp and the '>50 pinned at 100' anchor of the tail to the Still-judgement ledger. Name PEN_MAX in the judgment inventory with 'reaches: closing probability, both recommended asks, both scores'. Badge the P_C tile 'aggregate x judgment'. In optNote's range sentence say the end that wins also turns on the judgment gap-penalty scale. In the Data tab, give the PEN_MAX flip point (about 0.43 at the default) beside the FAN_S and theta flips.

### R1-2. The 'Outcome distribution' scenarios are percentiles of the price if the deal closes, but they are labelled as outcome percentiles and leave out the no-sale outcome

- **Key:** `price:scen:outcome-percentiles-conditional-on-close-unlabelled`  
- **Severity:** medium  
- **Where:** index.html render(): #scen cards (lines ~4392-4402, 'Bear/Base/Bull' with '8th–22nd / 38th–62nd / 80th–94th percentile' under the static heading 'Outcome distribution', line 1933); hero focal legend drawOrbit() lines 3605-3606 ('Bear case' / 'Bull case'); scenarios built from out.scen = q(.08..94) in model() line 3029

**Why it is wrong.** A bear case for a sale process that leaves out the model's own most likely bad outcome misstates the downside. The percentile labels claim an unconditional meaning they do not have. The panel tells a seller that overpricing improves the bear case while the chance of getting nothing rises from 32% to 58%. The quantiles are correct as conditional quantiles, but presenting them as the 'outcome distribution' is a conceptual error, not a styling choice.

**Verifier (reproduce).** Confirmed at a6d235c. The fan is deliberately the price given a close (AUDIT.md:297-303 treats price as independent of closing, so P_C×E[P] is consistent). That modelling choice is labelled. The scenario panel's wording is not: nothing in the heading, the percentile lines or the hero 'Bear case' legend says 'if it closes', and no no-sale line appears. As a result the bear band improves (2.64→2.66 low end, 3.16→3.64 high end) while P(no sale) rises from 32.3% to 58.1%. This is a labelling defect, not a maths one: the quantiles are correct as conditional quantiles. Severity medium to low.

**Fix (as proposed).** Rename the panel and the pct lines to the price if it closes, e.g. 'Price if it closes' and '8th–22nd percentile of closings'. Add a 'No sale' line or card showing 1−P_C. Alternatively, compute the bear/base/bull bands on the unconditional mixture (mass 1−P_C at no sale, P_C × the closing fan) and say which one is shown. Apply the same wording to the hero legend's 'Bear case' and 'Bull case'.

### R1-3. The 'Model value' and 'Expected multiple' tiles always carry a plain 'fitted' badge, though up to −27% / +32% of the number is the judgment quality position

- **Key:** `price:hero:model-value-badged-fitted-despite-judgment-quality-factor`  
- **Severity:** low  
- **Where:** index.html static hero markup line 1744 (o_msv, badge 'pv f' fitted) and line 1745 (o_mult); compare the time tile's dynamic badge in render() lines ~4064-4066 (o_t_pv switches to 'aggregate × judgment' when the judgment multiplier is active)

**Why it is wrong.** Provenance badges are meant to say how measured a figure is (AUDIT fix #10 relabelled the realised price and proceeds for exactly this reason). The time tile already flags its judgment multiplier. The value tile's judgment factor is larger and is shown as fitted, which overstates how measured the headline value and multiple are. The tooltip text cannot rescue a badge that is wrong.

**Verifier (reproduce).** Confirmed, low severity. The judgment is disclosed: the tile tooltips say '(that placement is judgment)' / 'times the quality position (judgment)', and the hero's o_qband caption says 'that placement is mostly judgment'. So the factor is not unlabelled. The visible provenance badge is still wrong, though. It reads plain 'fitted' while 14.6% of the default number (−27%/+32% at the extremes) comes from a factor the page itself badges as judgment. The time and closing-probability tiles switch to '× judgment' when their judgment multipliers are active, so this tile is inconsistent with the page's own convention. Fix: set these badges dynamically, as o_t_pv does.

**Fix (as proposed).** Set the o_msv and o_mult badges in render() as o_t_pv does: 'fitted × judgment' (class j) whenever |qFactor−1| exceeds a small tolerance, with a title giving the fitted value and the ×qFactor placement. Keep plain 'fitted' only at qFactor = 1.

### R1-4. Buyer EV, 'pursue first' and 'pays most' price each buyer at its full V_j, above the ask that caps every realised price

- **Key:** `buyers:ev:vj-priced-above-ask-ceiling`  
- **Severity:** medium  
- **Where:** index.html model(): line 2878 (EV:PE*PCj*Vj), 2880 (out.best), 2920-2921 (thin-pool re-sort); render: hero o_bb (4095), buyer table 4210-4217, eq_bs 4222-4227 ('pays most -> $V_j')

**Why it is wrong.** The model's own price block treats the ask as a ceiling: 'lower- and main-street deals essentially never close above it', and P(W) = softMin(W*A*(1+comp), ceil). EV_j already reads the ask through P_C,j, whose gap penalty falls as the ask rises, but it prices the deal at V_j with no ceiling. So the ranking rewards strategic buyers for value this listing cannot capture, and the decision-relevant 'Pursue first' tag in the hero depends on money the model elsewhere says never arrives. The two halves of EV are inconsistent: the probability depends on the ask, the price does not.

**Verifier (reproduce).** Present at a6d235c and a genuine defect. In model() line 2892 the EV is EV:PE*PCj*Vj (re-sorted at 2934-2935), with no ceiling. The price block (line 2957, out.ceil=softMin(s.ask,V*RHO_MAX)*askCeil, and Pc=softMin(Pf,ceil)) says no realised price exceeds the ask, yet the table, now headed 'Price it would pay', shows $5.19M on a $3.24M listing. The 'pursue first' ranking therefore rewards money the model elsewhere says never arrives. The pursue-first badge being judgment does not cover this: the mechanism itself contradicts the model's own ceiling. The fix batch did not touch it. The round-0 relabel to 'Price it would pay' makes the contradiction more explicit.

**Fix (as proposed).** Price each buyer through the same ceiling, e.g. EV_j = PE_j*PCj*softMin(V_j, r.ceil), or better the anchored buyer price softMin(V_j*A(ask/V_j)*(1+comp), ceil). Present V_j as willingness to pay and show the ask-capped figure beside 'pays most' (e.g. 'would pay $5.19M; this ask caps it at $3.24M').

### R1-5. Buyer-specific close probability ignores how the ask compares with that buyer's own value

- **Key:** `buyers:pcj:gap-read-against-model-value-not-buyer-value`  
- **Severity:** low  
- **Where:** index.html model() line 2877 (PCj = clamp(out.PC*(0.80+0.42*PE))) and 2920; buyer table column 'Closes if engaged'; star-map brightness

**Why it is wrong.** Closing falls with the gap between ask and value because buyers will not pay above what the business is worth to them. Once the console gives each archetype its own value V_j, the buyer-level close rate should read the gap against V_j. As it stands, the table says a buyer asked 45% above what it would pay closes 95% as often as one asked 1% below, so the 'Closes if engaged' column and the EV ranking carry no price information.

**Verifier (reproduce).** Present and not labelled. The buyer-level close rate is the aggregate P_C (gap read against V) times an engagement factor, so it never depends on the buyer's own price V_j. At 1.25V the table says MBO closes at 95% of the strategic's rate (.451/.477) while being asked 45% above what it would pay. Neither the Data-tab judgment rows nor the 'Closes if engaged' header or lede say the buyer close rate ignores the buyer's valuation. The BUYERS judgment row covers fit functions, synergy shares, multiple factors and phi, not the PCj form. Low severity, since P_C and proceeds use the aggregate, but it feeds EV_j, the pursue-first ranking and the star brightness.

**Fix (as proposed).** Compute PCj from the gap to that buyer's value: fitClose(ask, V_j, chan, Vbase).p x thinF x (0.80+0.42 PE), clamped. Keep the aggregate P_C as the calibrated figure for proceeds. Otherwise state in the column header that the buyer close rate does not depend on the buyer's valuation.

### R1-6. Above about $5.9M of model value the risk tile shows the risk of a capped $5M SBA note, without saying so

- **Key:** `risk:fitrisk:sba-cap-silently-binds-large-deals`  
- **Severity:** medium  
- **Where:** index.html fitRisk (loan=clamp(R.loan_share*price, R.loan_range)), hero tile o_risk render (around line 4072), Data tab Model V coefficient row 'ln(loan) at 4 years on book, loan = 85% of price'

**Why it is wrong.** For any deal above $5.88M the headline is the charge-off risk of a $5M 7(a) note. It is flat in deal size, carries the lowest table spread (1.42) and is shown as below-average risk (0.47x). Neither the tile, the tooltip nor the Data tab says the 7(a) cap binds, and the Data tab states that the loan is 85% of the price. The page before this round deliberately suppressed the observed-band line for deals of $5M and up ('7(a) loans cap at $5M, so there is no observed band above it'); this integration dropped that guard and keys the band on the clamped note. A reader sees an SBA-calibrated, below-average risk figure for a deal SBA financing cannot structure.

**Verifier (reproduce).** Present at a6d235c and genuine. The only place the cap is stated is a code comment ('held inside the 7(a) range'). The UI says the loan is 85% of price, and the tile shows a flat, below-average (0.47x) risk and the observed 2-5M band for deals of any size above about $5.9M. This also regresses an earlier audit fix that suppressed the band line at $5M and up. Severity medium.

**Fix (as proposed).** When R.loan_share*V exceeds R.loan_range[1], say so in the tile and tooltip, for example 'SBA 7(a) note capped at $5M (X% of the price): risk shown is for that note'. Either drop the rel multiple and the observed-band line there or mark them as not comparable. Change the Data tab row to 'loan = 85% of model value, held inside the 7(a) range $25K-$5M'.

### R1-7. Data tab says the prime rate feeds the survival risk, but it cancels exactly and moves no figure

- **Key:** `risk:datatab:prime-claimed-to-feed-risk`  
- **Severity:** low  
- **Where:** index.html renderData, Aggregate panel note (line ~4632: 'Three more published aggregates feed the survival risk ...: the prime rate (7.00%, Fed H.15) for the survival risk') and the Fitted-from-public-data row 'SBA loan rate in the survival-risk model ... WSJ prime 7.00% + ...'

**Why it is wrong.** Prime enters sbaRate only to be removed again in fitRisk, so no displayed number depends on it. fit/README.md says this correctly ('the survival risk reads only the spread over prime'), and the hero tooltip says the rate level is 'not applied'. The Data tab still lists the prime as an input that feeds the survival risk and presents the 'SBA loan rate' as the model's input. A reader would expect a prime change to move the risk, and it never does.

**Verifier (reproduce).** Present and genuine, but low severity. The Data tab names the prime as an aggregate that feeds the survival risk, yet the prime cancels exactly and no displayed number depends on it. This contradicts the tooltip and the README. A text-only defect.

**Fix (as proposed).** Say that the survival risk reads only the table spread over prime, that the prime level is not used (with the rate_level note), and drop the prime from the list of aggregates that 'feed the survival risk'. Alternatively, rename the row to 'SBA spread over prime by loan size'.

### R1-8. Data tab says the shipped 8-year level is in the upper part of its range, but it sits below the middle

- **Key:** `risk:datatab:shipped-level-upper-part-false`  
- **Severity:** low  
- **Where:** index.html renderData, Model V check 'Population level across specifications and reference periods' (line ~4592: 'The shipped level is in the upper part ...'); MODELS.risk.base_cif.note ('the shipped 4.7% sits in the upper part of the combined 4.0-5.7%')

**Why it is wrong.** 4.7% is the top of the specification range (4.04-4.70%) but in the lower half of the combined range the row displays. The reasons given after the colon (the two-year forecast over-predicted at O/E 0.82; FY2024-26 loans run at 0.66x) argue that the level is if anything high. The sentence wrongly reassures the reader that the shipped figure already sits at the conservative end of the displayed range.

**Verifier (reproduce).** Present and genuine, but low severity. The claim is false against the range shown beside it: 4.7% is below the 4.85% midpoint of 4.0-5.7%. It is only true of the spec range (4.0-4.7%), which the sentence does not name. The reasons given after the colon argue the level is high, which compounds the false reassurance.

**Fix (as proposed).** Say it is 'at the top of the specification range and just below the middle of the combined range', or drop 'upper part'. Make the same change in MODELS.risk.base_cif.note.

### R1-9. The state and 6-digit row quotes a CV AUC of 0.820 to 0.828, a different metric from the model's 0.718 out-of-sample AUC, with no label

- **Key:** `risk:datatab:corpus-auc-different-metric`  
- **Severity:** low  
- **Where:** index.html renderData, 'Everything else in the corpus' Added table, State charge-off effects row (line ~4835: 'with 6-digit: CV AUC 0.820 &rarr; 0.828')

**Why it is wrong.** Shown unqualified, the row implies the shipped risk model discriminates at about 0.83 and that state effects belong to a model at that level. In fact the figure is an administrative-window AUC, and most of it is credit for time on book. It conflicts with the headline 0.718 two panels above. The same run also shows the 6-digit and state effects held only 0.44 of their size out of time on the calendar split, which the row does not mention.

**Verifier (reproduce).** Present and genuine, but low severity. The row quotes an admin-window AUC (an age-and-calendar null scores 0.775 on it) with no label, two panels after the model's 0.718 5-year AUC. It is also mislabelled a second way: the 0.820 base has neither 6-digit nor state effects, so 'with 6-digit' wrongly credits the whole +0.008 to state effects.

**Fix (as proposed).** Label it 'admin-window CV AUC (age and calendar alone: 0.775)', or quote the change in the 5-year AUC, which is the metric shown elsewhere.

### R1-10. The shipped fix for #11/#15 is incomplete: optCardNote says the walk-away programme 'pays through the value retained if the process fails' when that term is lower under the walk-away programme (it reads only the sign of ΔP_C and ignores that V differs between programmes)

- **Key:** `decisions:optCardNote:retained-value-reason-read-off-pc-sign`  
- **Severity:** medium  
- **Where:** index.html optCardNote() (about lines 3390-3416): `if(s.theta>0&&dPC<-1e-4) why.push(...value retained...)` in the kind 'different' branch; rendered as the subtitle of the second optimiser card (#optout)

**Why it is wrong.** The retained-value term is (1−P_C)·θ·V. When the two programmes contain different interventions, V differs between them as well as P_C. The utility programme often drops value-adding changes, so V falls by more than 1−P_C rises. Using the sign of ΔP_C as a stand-in for the sign of the term therefore names, as a source of the gain, a term that actually works against the programme. It can also miss the term when it is the only source of the gain. The fix for #11/#15 was meant to name 'only the differences that move, in the direction they move', so this is a false explanation on the console's headline recommendation card.

**Verifier (reproduce).** The defect is present at a6d235c. In optCardNote the line `if(s.theta>0&&dPC<-1e-4) why.push(...value retained...)` treats the sign of ΔP_C as the sign of the retained-value term. In the 'different' branch V also differs between the two programmes, so the card names as a source of gain a term that works against the utility programme, by $21k to $55k in the cases checked. The code comment says the reason is 'read off the two terms the proceeds objective leaves out', and the code contradicts it, so this is not a labelled judgment. It also makes the #11/#15 fix ('names only the differences that move, in the direction they move') incomplete, as the title says. Medium severity is fair: this is the headline recommendation card and the explanation is false.

**Fix (as proposed).** Compute the two extra terms directly: dRet = θ[(1−P_C,U)V_U − (1−P_C,V)V_V] and dDelay = −λ_T[(t_U+days_U) − (t_V+days_V)]. Name each only when it is positive, for example ordered by size. When one of them is negative, say that it works against the programme. Add a fuzz invariant: every term named after 'pays only through' is positive, and the named terms sum to at least ΔU − Δnet.

### R1-11. optNote's 'close to a coin toss' test is 1% of |U(rSell)|, a level that contains the whole delay charge λ·E[T]. The threshold shrinks to zero as the cost of delay rises and then grows again, so the caveat appears, disappears and reappears for a nearly identical gain

- **Key:** `decisions:optNote:coin-toss-threshold-scales-with-utility-level`  
- **Severity:** low  
- **Where:** index.html optNote() line ~3316: `coin=gain<Math.abs(U(rSell))*.01`, with U = EVp+(1−P_C)θV−λ_T·tMean; its output decides whether the 'higher' and 'lower' texts carry the coin-toss sentence (#o_listnote)

**Why it is wrong.** Only utility differences mean anything. The level of U includes −λ·E[T], which both asks share almost entirely, and it can be any sign. A closeness test scaled by |U| therefore depends on an arbitrary offset. It also disagrees with the note's own tie rule, which is 1% of model value.

**Verifier (reproduce).** The defect is present: `coin=gain<Math.abs(U(rSell))*.01` at index.html:3315. U's level includes −λ·E[T] and changes sign as λ rises, so the threshold falls to about zero near U=0 and the flag is non-monotone in λ for a nearly constant gain. A $159 gain is not flagged while $200 and $122 are. A 1.05%-of-V gain is flagged even though the same note's range/tie rule uses 1% of V. No document labels or justifies the |U| scaling. tests/model.test.js:619 only pins the formula as written, so it does not count as a label. Low severity: this is wording.

**Fix (as proposed).** Scale the coin-toss test by model value, for example gain < 0.01·V, matching the range or tie rule. Alternatively, scale it by the stakes that actually differ between the two asks, such as |EVp(rSell) − EVp(rKeep)| plus the retained and time terms. Add a test that the coin flag is monotone in λ_T for a fixed gain-to-V ratio.

### R1-12. The sensitivity note says that, with the ask binding, improving the business does not raise what the listing collects, but the bar beside it shows up to 40% of the full pass-through (a quality response as large as the ask's own). The note also switches off at ask = V while the ask still binds

- **Key:** `decisions:sensflat:binding-ask-note-denies-quality-pass-through`  
- **Severity:** low  
- **Where:** index.html render() sensflat IIFE (about lines 4331-4352): branch `if(r.askBinds&&over<0)` text '…improving the business raises what it supports (left) but not what this listing will collect (right, largest quality response $X). Repricing is the lever…'

**Why it is wrong.** The ceiling binds only at the median: 48–74% of the realised-price fan sits at the ask. The quality levers still move expected proceeds through the uncapped slices. The note's categorical 'not what this listing will collect' contradicts the number it prints in the same sentence. Near V, quality is as strong a lever as repricing, so 'Repricing is the lever' does not single out the ask. The trigger is a sign test on the gap (over < 0) on top of askBinds, so the note flips on and off at ask = V even though nothing about the ceiling changes there. It also prints '0% under'.

**Verifier (reproduce).** The defect is present. The note says categorically that quality does 'not' raise what the listing collects, yet in the same sentence it prints a response worth about 40% of full pass-through, equal to the repricing response it calls 'the lever'. The code comment's claim that 'an underpriced listing also cannot turn better quality into a bigger cheque' is contradicted by the model's numbers, because only about 52% of the fan sits at the ceiling. The over<0 gate turns the note off at ask = V while askBinds and capShare are unchanged. Small gaps print as '0% under'. One nuance: the medical $6M disappearance at .98×V comes from askBinds flipping, not from the over<0 gate. The ask=V flip on the default case is enough to show the gate issue. No document labels this. Low severity.

**Fix (as proposed).** Phrase it quantitatively, for example 'collects only about X% of it' with X = qMax/(P_C·|dV|), and show it only when the share is small (for example below 25%). Key the branch on capShare or askBinds alone, not on the sign of the gap. Format the gap with one decimal or omit it when it is under 1%.

### R1-13. The intervention table's 'Net days' still measures the time to close on the median after the E[T] fix, so the same change takes a different number of days in the table and in the optimiser's 'Expected days' tile (mean)

- **Key:** `decisions:interventionTable:net-days-on-median-not-mean`  
- **Severity:** low  
- **Where:** index.html interventionTable() line ~3477: `dT=r1.tMed-rb.tMed`, dTnet=it.days+dT, rendered as the 'Net days' column of #intbl; compare with optimize() recV/recU t:r.tMean and the card tile 'Expected days' (Math.round(sel.t+sel.days))

**Why it is wrong.** Round-0 findings #6/#13/#19 moved the console onto the mean time to close (out.tMean) for the delay cost and the 'Expected days' tile. The intervention table still differences the median, and its column header does not say so. Two panels therefore report different elapsed-time effects for the same change. The gap is 28–44% of each Δt and reaches 6–7.5 days on the reprice row.

**Verifier (reproduce).** The defect is present: `dT=r1.tMed-rb.tMed` at index.html:3465. The column header is just 'Net days', and neither the static caption nor the footnote says it uses the median. The optimiser tile right below says 'Expected days' and has a title naming the MEAN. So for the same reprice-only change one panel shows −7 days and the other −13. The choice is unlabelled, which per the rules makes it a defect. Mitigating point: the hero tile is labelled 'Median time to close', so a median delta is defensible if the column says so. The gap matters only at high asks; at the default it is about 1 day. Low severity.

**Fix (as proposed).** Use r1.tMean − rb.tMean in interventionTable (dT and dTnet), so 'Net days' is execution plus the change in the expected time to close, as in the optimiser tile. Alternatively, label the column 'Net days (median)'. Add a test that the reprice row's dTnet equals the difference in the optimiser's expected days for the reprice-only programme.

### R1-14. Sensitivity bars for customer concentration, channel concentration and the asking price show the effect of a cut, under headers and an equation that say ∂y/∂x, so their signs read backwards

- **Key:** `presentation:sensitivity:inverted-rows-shown-under-plain-derivative`  
- **Severity:** medium  
- **Where:** index.html SENS table lines 3519, 3524, 3525 (inv:true); sensitivity() line 3549 (if(v.inv){dV=-dV;dE=-dE;dP=-dP;}); render() lines 4320 and 4326 (divBars passes only o.n, never o.unit); column headers lines 1857 and 1861 ('What the business supports ∂V/∂xᵢ', 'What the seller can expect ∂E[proceeds]/∂xᵢ'); eq_d ('reported = ∂y/∂x_i·σ_i'); eq_ds line 4366 prints a unit only for the top quality lever.

**Why it is wrong.** The bars sit under ∂V/∂xᵢ and ∂E[proceeds]/∂xᵢ, beside an estimator that says reported = ∂y/∂x·σ. Read that way, the panel says more customer or channel concentration adds $220k of value, and that raising an underpriced ask loses $90k. Both are the opposite of what the model computes, and at 2× value the ask bar turns blue and positive, which reads as advice to raise an already overpriced ask. Only owner dependence was renamed ('Owner independence') to match its flipped sign. The other three inverted rows were not.

**Verifier (reproduce).** Confirmed at a6d235c. Only own was renamed to 'Owner independence'. cc, plt and ask keep neutral names while their sign is flipped by inv:true (line 3549). One partial mitigation: when the ask binds below value, the #sensflat caption does say 'each 5% off the ask changes expected proceeds by −$90k', which states the direction for the ask row. Nothing states it for the two concentration rows, and at 2×V the caption is empty and the ask bar shows +$19k. Not in KNOWN_FINDINGS or the AUDIT history. Genuine, medium.

**Fix (as proposed).** Name each inverted row for the direction it measures, as was done for owner dependence: 'Less customer concentration', 'Less channel concentration', 'Asking price, 5% lower'. Alternatively, print o.unit beside every bar, or drop inv and report the plain ∂y/∂x·σ that the headers promise.

### R1-15. The earnings input is labelled 'SDE / EBITDA', but every formula reads it as SDE: entering EBITDA, as the label allows, undervalues by 26% and mislabels the EBITDA multiple

- **Key:** `presentation:rail:earnings-input-labelled-sde-or-ebitda-but-read-as-sde`  
- **Severity:** medium  
- **Where:** index.html line 1652 (label and aria-label 'Normalized earnings (SDE / EBITDA)'); fitValue() lines 2115-2176 (ln SDE, SDE hinge, margin = sde/rev); hero o_mult line 4137 (xx(r.M)+' SDE', then M×wedge labelled ' EBITDA'); sdeEbitdaWedge() lines 2094-2112.

**Why it is wrong.** The value equation is fitted on BIZCOMPS SDE: the ln SDE term, the SDE hinge and the SDE margin all assume the input is SDE. The hero's EBITDA multiple also assumes it, because it divides the input by the SDE-to-EBITDA wedge. The label tells the user either measure is acceptable, but half of the stated inputs produce a value about a quarter too low and a wrong EBITDA multiple.

**Verifier (reproduce).** Confirmed. The fitted value equation is SDE-only, and the hero's EBITDA restatement treats the input as SDE. The label allows EBITDA, and EBITDA entered there understates value by about 26% at the defaults. The self-audit rows ('$1.5M EBITDA', '$20M of EBITDA') also feed EBITDA-named figures into the same input, which shows the mixing is not a labelled convention. Genuine, medium.

**Fix (as proposed).** Relabel the field 'Normalized earnings (SDE)' and add a note that EBITDA must be grossed up by owner compensation. Alternatively, add an SDE/EBITDA switch that converts EBITDA to SDE with sdeEbitdaWedge before calling model().

### R1-16. At 390px every label in the buyer map and the time-to-close chart renders at 3.2–5.1px, and the 90/180/365-day closed shares appear nowhere else

- **Key:** `presentation:charts:svg-labels-3px-at-390`  
- **Severity:** medium  
- **Where:** index.html #tcurve (viewBox 760×270, line 1815) and #starmap (viewBox 980×470, line 1831), scaled to the column by CSS at line 6990 (#starmap,#tcurve{width:100%;height:auto}). drawCurve() (font-size 10.5–12.5) and drawStars() (font-size 10–11.6). model() line 2860 sets r.t90/t180/t365, which render() uses only inside the SVG.

**Why it is wrong.** At phone width the buyer prices, engagement rates and the share of closings by 90, 180 and 365 days cannot be read, and the last three are shown nowhere else in text. The equations have a 60% shrink floor before they switch to scrolling. These charts have no floor and shrink to under a third of their design size.

**Verifier (reproduce).** Confirmed. The 90/180/365-day closed shares exist only inside an SVG whose text is 4–5px at phone width, and the buyer map is about 3px. The buyer prices and engagement are recoverable from the buyer table, which the finding itself acknowledges. Not covered by prior fixes (AUDIT mentions phone-width table scrolling only). Genuine, medium.

**Fix (as proposed).** Give both SVGs a min-width (for example 640px) inside a horizontally scrolling wrapper like .tw, or switch to a compact mobile layout with larger font sizes relative to the viewBox below about 600px. Also add the 90/180/365-day shares to the aria-label or to a text line under the chart.

### R1-17. The confidence panel labels its 80% interval 'from fitted residuals', but it shows the ask-capped realised-price interval: 1.17× wide against the fitted band's 3.32×, and it moves with the ask

- **Key:** `presentation:eq_cs:interval-labelled-fitted-residuals-is-ask-capped-price`  
- **Severity:** low  
- **Where:** index.html line 1941 (lbl 'Analysis confidence · interval from fitted residuals'); eq_cs line 4496 (prints r.q(.10), r.q(.90) of the realised-price fan); the code comment just above says 'sigma is the fitted BIZCOMPS residual band'; the Method panel (#srcs) on the same tab says 'The p10–p90 span runs 0.51×–1.69× the point estimate — report the range'.

**Why it is wrong.** An interval taken from the fitted residuals cannot depend on the asking price. This one has been narrowed to FAN_S = 0.80 of the spread, moved by anchoring and capped at the ask. Printed under 'interval from fitted residuals' next to 'High' confidence, it overstates the model's precision about eightfold in ratio terms. The same tab tells the reader to report 0.51–1.69×.

**Verifier (reproduce).** Confirmed. The printed interval is the narrowed (FAN_S 0.80), anchored and ask-capped realised-price fan, and it moves with the ask. The panel label calls it an interval from fitted residuals. The eq_cs text itself says 'price if it closes', which is accurate, so the defect is the panel label and the contrast with the 0.51–1.69× instruction. Distinct from the R1 scen percentile finding. Genuine, low.

**Fix (as proposed).** Relabel the interval 'price if it closes, 80% interval (realised-price fan, capped at the ask)', or print the fitted residual interval [V·p10, V·p90] beside it, which matches the existing code comment.

### R1-18. The survival-risk tile carries a plain 'fitted' badge with no tooltip, although 17% of its 10-year headline is the judgment tail factor, and its '(0.56×)' ratio is never explained on the Console

- **Key:** `presentation:hero-risk:fitted-badge-covers-judgment-tail-and-unexplained-ratio`  
- **Severity:** low  
- **Where:** index.html line 1746 (static <span class="pv f"> with no title); render() lines 4146-4166 (headline pc(k.p,1) plus '('+k.rel+'×)'; e.title omits both the tail and the ratio); fitRisk() line 2275 (pTerm = p8*R.tail_factor) and line 2282 (rel = pTerm/base_cif.term). The Data tab judgment ledger (lines 5021-5023) lists 'SBA tail factor ×1.20 … matched to acquisition-loan size by judgment'.

**Why it is wrong.** The badge disagrees with the console's own judgment ledger. The time tile switches its badge to 'aggregate × judgment' when its judgment multiplier is active, and this tile does not. The bare '(0.56×)' gives no reference point, so a reader cannot tell what the risk is 0.56× of. This sits alongside the R1 finding on the model-value badge but concerns a different tile and a different judgment.

**Verifier (reproduce).** Confirmed. The round-0 fix #21 moved the tail factor into the judgment count but left the hero tile badged plain 'fitted', and the '(0.56×)' ratio has no referent on the Console. Same pattern as the R1 model-value badge finding, but a different tile and judgment, so not a duplicate. Genuine, low.

**Fix (as proposed).** Badge the tile 'fitted × judgment', with a title such as '8-year fitted 2.7% × 1.20 tail for years 9–10 (judgment)'. Label the ratio '0.56× the average acquisition loan (5.6%)'.

### R1-19. eq_p prints the gap-tail rate as k=0.0011 when it is 0.0011356, so the formula on screen gives a different penalty and P_C from the boxed figures beneath it

- **Key:** `presentation:eq_p:tail-rate-k-rounded-to-two-significant-figures`  
- **Severity:** low  
- **Where:** index.html eq_p line 4260 (k=${GAP_TAIL_K.toFixed(4)}); eq_ps prints only the resulting penalty.

**Why it is wrong.** Substituting the general form's printed constant does not reproduce the substituted line beneath it, and the error grows with the gap.

**Verifier (reproduce).** Confirmed. The printed general-form constant does not reproduce the boxed penalty and P_C beneath it, and the gap widens with g. The auditor's 'earnings $120k: 0.572 vs 0.569' case did not reproduce with rev 300k (I get 0.894 vs 0.888). The 60k and 10×V numbers match. Genuine but minor (display precision), low.

**Fix (as proposed).** Print k to three significant figures (k=0.00114), or show e^{−k(g−100)} in eq_ps.

### R1-20. eq_v's h(SDE), m and e_i are never defined or given values on the Console, and eq_vs jumps from the general form straight to $3.28M; with h=0 and e_i=0 the printed coefficients give $1.46M

- **Key:** `presentation:eq_v:general-form-terms-never-valued`  
- **Severity:** low  
- **Where:** index.html eq_v line 4233 and eq_vs line 4236. The hinge is defined only on the Data tab (line 4615). The same applies to eq_a (A_max, line 4240) and eq_comp (κ, line 4314), whose substituted lines print only results.

**Why it is wrong.** The equation panels are meant to let a reader check each number against its formula. The largest term in the value equation is undefined on the page, so the general form cannot be reconciled with the substituted line. This is the same defect as the R1 eq_ts 'h undefined' finding, in a different panel.

**Verifier (reproduce).** Confirmed for the core claim: h(SDE) is undefined on the Console, and m, e_i, A_max and κ are never valued, so the general forms cannot be reconciled with the substituted lines. The lede names margin and the industry effect in words only. One sub-claim is not a defect: at ρ=2 the printed A=1.189 equals A(ρ̃=1.50). eq_a's general form explicitly uses ρ̃ = softmin(max(ρ,.35), 1.5), and the multiple table says 'flat past 1.50×', so that part is consistent. Distinct from the round-0 eq_v units fix and the R1 eq_ts h finding. Genuine, low.

**Fix (as proposed).** In eq_vs, print h(SDE)=2.27 (with 'h = ln(SDE/$150k), floored at 0'), m=0.242 and e_i=−0.087. In eq_as, print A_max=1.30 and ρ̃. In eq_comps, print κ=0.03.

### R1-21. The multiple table's 'Bounds on the stack' row says the multiple is held to 0.42–1.85× base, but the floor that actually binds is an absolute 0.90×

- **Key:** `presentation:multbl:stack-bounds-row-misstates-floor`  
- **Severity:** low  
- **Where:** index.html model() line 2711 (M = clamp(base*(1+sum), Math.max(.90, base*.42), base*1.85)); render() line 4204 (row text 'net held to −55%…+85%, multiple to 0.42–1.85× base').

**Why it is wrong.** The row exists to explain why the judgment multiple differs from base × (1 + net). It names a bound that cannot bind and omits the one that does, so 0.90× cannot be reconciled with the rows above it. The stack is labelled 'not used', so the impact is limited to the explanation.

**Verifier (reproduce).** Confirmed. The row names a bound that cannot bind and omits the absolute 0.90× floor that produces the 0.90× shown. Impact is limited because the stack is labelled 'not used'. Genuine, low.

**Fix (as proposed).** Change the row text to 'multiple held to max(0.90×, 0.42× base)–1.85× base', or drop the unreachable 0.42 term.

### R1-22. The Console source note and the Data tab say Pepperdine termination 'has risen every year since the 2020–21 trough', but the shipped series falls from 28% to 27% in 2023

- **Key:** `numbers:srcs:termination-risen-every-year-false`  
- **Severity:** low  
- **Where:** /tmp/claude-0/r1snap/index.html:5383 (#srcs on the Console), :4734 (Data-tab 'Termination trend' row, with a hard-coded 32%), :2390 (fitClose comment). The same claim is in MODELS.close_and_timing.close_probability.recent_basis and trend_note.

**Why it is wrong.** The text makes a claim that the shipped series contradicts. It is offered as the reason the base rate uses only the three most recent years, so a reader checking it against the data finds it false. The Data-tab figure of 32% is typed in rather than read from the series, so it can drift.

**Verifier (reproduce).** The text is contradicted by the shipped data. The model's computation is unaffected (intermediated_base_recent uses 2024-2026), so the impact is narrative only. Low severity.

**Fix (as proposed).** Generate the sentence from ib_termination_series, for example 'Termination troughed at 24% in 2020–21 and has risen since, to 32% in 2026 (27% in 2023, down from 28%)'. Read the 2026 value from the series on the Data tab too.

### R1-23. The optimiser notes print the cost of delay through money(), so $1,450 a day reads as '$1k a day' (31% low) beside a dollar figure computed at $1,450

- **Key:** `numbers:optnote:cost-of-delay-rounded-to-thousands`  
- **Severity:** low  
- **Where:** /tmp/claude-0/r1snap/index.html:3317 and :3367 (optNote), :3400 (optCardNote): money(s.lamT)

**Why it is wrong.** money() rounds anything of $999.5 or more to whole thousands, which suits prices but not a per-day input that moves in $50 steps. The note prints a value 'worth $685' that was computed at $1,450 a day next to '$1k a day', so the printed λ and the printed dollar figure disagree. The rail and eq_us show the exact input.

**Verifier (reproduce).** Confirmed at optNote :3317 and :3367 and optCardNote :3400. The printed λ is 31% low at $1,450, 13% low at $3,450 and 20% high at $2,500, and it sits beside a dollar figure computed at the exact λ. Presentational, low.

**Fix (as proposed).** Format λ the way labels() and eq_us do, for example '$'+s.lamT.toLocaleString('en-US'), in optNote (both places) and optCardNote.

### R1-24. The multiple table's 'Bounds on the stack' row gives the multiple's bounds as 0.42–1.85× base, but the model also floors it at 0.90× absolute, so the displayed net and multiple do not reconcile

- **Key:** `numbers:multbl:judgment-floor-0.90-unlabelled`  
- **Severity:** low  
- **Where:** /tmp/claude-0/r1snap/index.html:2711 (M=clamp(base*(1+sum), Math.max(.90, base*.42), base*1.85)) against :4204-4209 (the multbl 'Bounds on the stack' and 'Judgement multiple' rows)

**Why it is wrong.** The row states bounds that are not the bounds the code applies. The 'net' and the 'Judgement multiple' figures then contradict each other on screen. When only the 0.90 floor binds, the row's right-hand column reads '−x% → −x%' (no change) beside a multiple that has moved. It is a judgment multiple labelled 'not used', so the impact is presentational.

**Verifier (reproduce).** The row states bounds that are not the ones applied, so '−55.0% net' and '0.90×' do not reconcile (1.63×0.45 = 0.73×). The row is the 'not used' judgment multiple, so the impact is presentational only. Low severity.

**Fix (as proposed).** Label the floor: 'multiple to max(0.90×, 0.42× base)–1.85× base'. Show Mraw → Mjudg in the row whenever the multiple clamp binds, or drop the 0.90 absolute floor.

### R1-25. The quality-position note renders 'here, the below the middle' for a percentile between 15 and 38

- **Key:** `numbers:qband:the-below-the-middle`  
- **Severity:** low  
- **Where:** /tmp/claude-0/r1snap/index.html:4095-4096 (lab strings) and :4110 ('here, the '+lab)

**Why it is wrong.** One of the five position labels is spliced after a fixed 'the ', which produces a broken phrase in the panel that explains the judgment placement. All other figures in the panel matched the model.

**Verifier (reproduce).** A grammar defect in the judgment-placement note, for any qPct in [0.15, 0.38). The other four labels read correctly after 'the'. Cosmetic, low.

**Fix (as proposed).** Use labels that read correctly after 'the' (for example 'lower part of the range'), or drop 'the' from the template and put it into each label.

### R1-26. Fix incomplete for presentation:closing-prob:thin-pool-not-in-badge-or-captions: the provenance key and the Data tab still say P_C conditions on the price gap (and size) only

- **Key:** `datatab:provenance:pc-conditions-only-on-gap`  
- **Severity:** medium  
- **Where:** index.html line 5350 (provenance pvkey 'Aggregate ... Conditions on deal size and price gap only'); line 4975 (Data tab 'What actually kills a signed deal': 'The closing model on this console conditions on price gap and nothing else.')

**Why it is wrong.** Round 0 fixed the Model I lede, the footer and the provenance bullet to mention the thin-pool factor. Two statements were missed. The provenance key still says 'only' size and gap, and the Data tab says the closing model 'conditions on price gap and nothing else'. That second sentence contradicts even the size conditioning. Both are contradicted by a 39-point swing in P_C from buyers contacted and a 9-point swing from deal size at a zero gap.

**Verifier (reproduce).** AUDIT_FINDINGS.md #16's fix list covered the §5-7 lede, the Data-tab Model I lede, the footer and the tooltip. It did not cover the pvkey or line 4975, and both still state the old claim. Line 4975's 'price gap and nothing else' even contradicts the size conditioning. The fitClose comment at line 2296 itself says 'Conditions on deal size, gap and pool ONLY'. The shipped fix is incomplete.

**Fix (as proposed).** Reword the pvkey to 'deal size, price gap and, below a typical pool, the number of buyers contacted (calibrated scale, judgment shape)'. Reword line 4975 to say the closing model conditions on deal size, price gap and pool depth, but on nothing that records why deals die (diligence findings).

### R1-27. The Data tab says E[T] is 28% above the median from $500K of value and 44% below it, but β is interpolated between $250k and $707k, so the premium is 31–34% around $500K

- **Key:** `datatab:model3:mean-over-median-step-at-500k`  
- **Severity:** low  
- **Where:** index.html renderData() line 4810 ('charged per day on the MEAN time to close, which the log-logistic puts 28% above the median from $500K of value and 44% above it below'); the same claim is in the model() comment above out.tMean (~line 2853)

**Why it is wrong.** fitTiming() reads β through bandInterp() on BAND_KNOTS, which interpolates in ln(Vbase) between the $250k and $707k centres. The same paragraph says so ('β is interpolated in ln(value) between the $250k and $707k band centres'). The delay-cost premium therefore changes continuously from 44% at $250k to 28% at $707k; there is no step at $500K. Between those sizes the stated figures are off by up to 10 points, and in both directions.

**Verifier (reproduce).** There is no step at $500K. The premium is 34% at $447k (not 44%) and 31% at $552k (not 28%). The same Data tab paragraph says β is interpolated between $250k and $707k, which contradicts the step. The code comment at lines 2855-2856 ('28% ... to 44%') is looser but also keys the figures to $500K. Low severity.

**Fix (as proposed).** Say 'from 44% above the median at $250k of value or less to 28% from $707k up, interpolated between' in the Data tab and the out.tMean comment.

### R1-28. The hinge paragraph credits the size hinge with R² 0.7255 → 0.7546 and error 30.8% → 28.4%, but MODELS says the hinge gave 0.7399 / 30.1%; the same tab credits 0.7399 → 0.7546 to the 6-digit effects

- **Key:** `datatab:model2:hinge-credited-with-6digit-and-calibration-gains`  
- **Severity:** low  
- **Where:** index.html renderData() lines 4628-4631 ('both cross-validated fit and error improved: R² ${V.v1_comparison.cv_r2_log} → ${V.cv_r2_log}, median error ... → ...') vs line 4924 ('6-digit industry effects ... R² 0.7399 → 0.7546')

**Why it is wrong.** The paragraph compares v1 with the current v3, so it attributes to the hinge the R² gain from the 6-digit industry effects (0.7399 → 0.7546) and the error gain from the median calibration (29.1% → 28.4%). The Data tab then credits the same 0.0147 of R² a second time, to the 6-digit effects. MODELS records the hinge's own effect as 0.7255 → 0.7399 and 30.8% → 30.1%.

**Verifier (reproduce).** The hinge paragraph compares v1 with v3 plus the calibration, so it credits the hinge with the 6-digit gain (0.7399→0.7546, which the same tab also credits to the 6-digit effects) and with the calibration gain (29.1%→28.4%). MODELS records the hinge's own step as 0.7255→0.7399 and 30.8%→30.1%. Low severity.

**Fix (as proposed).** Quote V.v2_comparison for the hinge (R² 0.7255 → 0.7399, error 30.8% → 30.1%), and attribute the remaining steps to the 6-digit effects and the median calibration.

### R1-29. 'Termination ... has risen every year since' the 2020–21 trough is contradicted by the shipped series, which fell from 28% (2022) to 27% (2023)

- **Key:** `datatab:model1:termination-risen-every-year-false`  
- **Severity:** low  
- **Where:** index.html renderData() line 4734 (Termination trend row: 'troughed at 24% in 2020–21, has risen every year since'); provenance list line 5383 ('Termination has risen every year since the 2020–21 trough of 24%'); fitClose() comment line 2390

**Why it is wrong.** The series the console ships falls one point from 2022 to 2023, so it has not risen every year since the trough. The page states this as a fact and badges it 'published'.

**Verifier (reproduce).** The shipped series falls from 28% in 2022 to 27% in 2023, so 'risen every year since' is false. The statement is badged 'published'. Low severity.

**Fix (as proposed).** Say 'troughed at 24% in 2020–21 and has risen since (28% in 2022, 27% in 2023, 32% in 2026)', or generate the sentence from ib_termination_series.

### R1-30. The Data tab says the loan-size hazard gap 'closes by year 6'; in the code it crosses zero at 5.4 years and reverses, so larger loans carry a higher charge-off hazard in years 6–8

- **Key:** `datatab:model5:size-gap-reverses-not-closes`  
- **Severity:** low  
- **Where:** index.html renderData() Model V table, line 4657 ('ln(loan) × years on book (to 6) ... and later: the gap closes by year 6'); fitRisk() age term

**Why it is wrong.** The table reads 'larger loans are charged off less often ... and later: the gap closes by year 6', which tells a reader the size effect fades to nothing. The shipped coefficients instead reverse it: from year 6, a ten-times-larger loan has a 16% higher charge-off hazard, and through the tail factor that carries into years 9–10.

**Verifier (reproduce).** The gap reaches zero at about 5.4 years and then reverses: a 10× loan carries about a 16% higher charge-off hazard from year 6. No history file labels the reversal as intended. The fitRisk comment at line 2229 repeats 'closes by year 6'. Low severity.

**Fix (as proposed).** Say 'the gap closes by about year 5.4 and reverses slightly after it (×1.16 per tenfold loan size in years 6–8, held there)', or cap the interaction so that it stops at zero if a reversal is not intended.

### R1-31. The '480 estimated from transaction outcomes' tally leaves out fitted tables the model reads and the page badges fitted, and counts 39 parameters fitted to listings and survey aggregates

- **Key:** `datatab:tally:fitted-count-omits-and-mislabels`  
- **Severity:** low  
- **Where:** index.html renderData() nFit, lines 4521-4534; tally label line 4539 ('estimated from transaction outcomes') and line 4545 ('transactions behind the fitted half')

**Why it is wrong.** The tally says it is 'generated from the live model constants' and that it counts what is 'estimated from transaction outcomes'. It misses at least 53 fitted values the model reads, 15 of them badged fitted on the same tab. At the same time, 39 of the 480 come from asking prices and survey aggregates, which by the tab's own tier table ('Unit of observation: one transaction') are not transaction outcomes.

**Verifier (reproduce).** At least 53 fitted values the model reads are missing from the 'estimated from transaction outcomes' count. The code comment excludes only FAN_S and ENG_SHARE, deliberately. Fifteen of the missing values sit in a row the same tab badges 'fitted'. The mislabel half is softer: SBA spread knots are 7(a) loan rates, which can be argued to be transaction data. sde_margin (19), quality weights (2) and buyer_mix (10) do come from listings or survey shares. The omission alone makes the finding real. Low severity.

**Fix (as proposed).** Add fan_quantiles, calibration knots, pif.sector and the LGD curve to nFit. Then either relabel the tile ('estimated from data: transactions, listings and survey tables') or split the 39 listing/survey-fitted values into their own count.

### R1-32. The judgment tally and the IND inventory row count the 16 industry display names as hand-set parameters (IND × 10 fields includes 'n')

- **Key:** `datatab:tally:judgment-count-includes-industry-names`  
- **Severity:** low  
- **Where:** index.html renderData() nJudg line 4514 and the IND inventory row lines 4996-4997 (Object.keys(IND[first]).length = 10)

**Why it is wrong.** 'n' is the dropdown label string, not a number anyone chose, yet it is counted 16 times among the 'hand-set numbers ... the magnitudes are invented'. That inflates the judgment headline and the IND row by 16.

**Verifier (reproduce).** The dropdown label is counted 16 times as a hand-set parameter whose 'magnitudes are invented'. That inflates both the judgment headline and the IND row by 16. Low severity.

**Fix (as proposed).** Count only the numeric IND fields (filter on typeof v === 'number'), and say '× 9 fields'.

### R1-33. The self-audit row calls BizBuySell's 90.5% 'the fit's own target', but FAN_S was set to the multi-source average, so the row reads 89.0% and passes only through its ±2.5-pt window

- **Key:** `datatab:selfaudit:fit-consistency-target-mislabelled`  
- **Severity:** low  
- **Where:** index.html renderCalib() lines 5324-5326 (row 'Fit-consistency check ... the fit's own target: BizBuySell deal-level 91.7% on the ask at sale = 90.5% on the first ask')

**Why it is wrong.** Only s ≈ 0.66 reproduces the quoted BizBuySell target; the shipped 0.80 was chosen from an average over several sources. Labelling 90.5% as 'the fit's own target' tells the reader the calibration hits it, but the row shows 88.95%, 1.55 points short, and it passes only because the window is ±2.5 points.

**Verifier (reproduce).** Only s ≈ 0.66 reproduces the 90.5% the row calls 'the fit's own target'. The shipped 0.80 targets a multi-source average, so the row reads 1.55 pts short and passes only through its ±2.5-pt window. The label misdescribes the calibration target. Low severity.

**Fix (as proposed).** Label the target as the source-average calibration, or show BizBuySell's 90.5% as one of several sources (with the model's 89.0% beside it), and tighten or explain the window.

### R1-34. The cross-source check quotes a 'fitted' sector spread of 0.86–1.33. The shipped sector effects for the same 11 DealStats sectors span 0.86–1.43.

- **Key:** `datatab:crosscheck:dealstats-fitted-range-stale`  
- **Severity:** low  
- **Where:** index.html renderData() line 4822 ('r = +0.887 across 11 NAICS sectors, with matching spread (0.86–1.33 fitted, 0.78–1.35 measured)'), hard-coded

**Why it is wrong.** The page presents the agreement as a check on the shipped Model II industry effects, and says the tab is generated from live constants. The quoted fitted range does not match the shipped effects under either normalisation: sector 52 alone sits at ×1.43. The r = +0.887 is a hard-coded figure that cannot be reproduced from anything the page shows.

**Verifier (reproduce).** Under neither normalisation does the quoted fitted range match the shipped effects: sector 52 sits at ×1.428. The r cannot be reproduced from anything shipped: the 3 untabulated sectors' DealStats values are absent, and on the 8 shown r is 0.46. The figure is probably stale from a pre-v3 fit. Low severity.

**Fix (as proposed).** Recompute r and the range from V.industry_effects (or the 6-digit effects the console actually uses) against the DealStats series, generate the sentence from them, and show all 11 sectors in the table.

## Rejected by verification

| Key | Why rejected |
|---|---|
| `closing:thinf:same-expected-offers-different-pc-across-industries` | The numbers reproduce: fitness at 29 buyers has nPool 0.996, nEngRef 0.996, thinF 1.000 and P_C 0.608, while distribution has nPool 0.998, nEngRef 2.030, thinF 0.727 and P_C 0.442. But this is a deliberate judgment, labelled on the page and in AUDIT.md.  (1) The judgment inventory's IND row says IND buyers 'is also the typical pool that the thin-pool factor and the competition premium are measured against, so below a… |
| `closing:rendercalib:close-rate-rows-restate-base-input` | The numbers reproduce. lmm (mfg $1.5M, chan 'intermediary', ask = V) gives P_C 0.6967. ulmm (mfg $3.5M at V) gives P_C 0.6967 with base 0.6967, pen 0 and thinF 1, which equals intermediated_base_recent 0.6967. Both stay at 0.6967 with PEN_MAX at .05 or .95, and unforced lmm reads 0.6866 (u 0.886, Vbase $4.16M).  But this is intended and documented, and no displayed number or claim is wrong. (1) Forcing the intermedia… |
| `closing:sensflat:floor-caption-says-penalty-at-maximum` | Already fixed at this snapshot, and the reproduction does not hold.  The 2% floor is gone: fitClose returns clamp(base*(1-pen),0,.95), with the comment 'no floor: a 2% floor froze the probability ...'. The P_C floor sentence the finding describes no longer exists.  Run at r1snap (framework default, ask = k×V): - 26x: pen 0.9640, P_C 0.0244, max/dP/ 4.8e-3 - 30x: pen 0.9771, P_C 0.0155 (not 0.0200), max/dP/ 3.5e-3 (no… |
| `price:realisation:benchmark-ratio-times-mainstreet-industry-factor` | The arithmetic reproduces: fitTiming(3.49e6,'medical') gives 0.9637×1.0291=0.9917, (2e7,'ecom') gives 1.0200×1.0571=1.0782 and (3.49e6,'wash') gives 0.9637×0.9331=0.8992. Three things refute it as a defect. (1) It is intended and documented. The model's own source string (MODELS.value.price_realisation_by_industry.source) and the fitTiming comment (index.html 2428–2434) say: 'Multiplies the IBBA size-band figure… Lev… |
| `scores:render-caption:proceeds-optimum-called-optimal-against-walkaway-advice` | The reproduction holds, but the behaviour is intended and documented, and every number shown is correct. Playwright on r1snap with v_th=78 and v_ask=6135666 reads business 79 'at the optimal ask of $4.50M', Omni 19, and the caption 'The ask costs 30% of expected proceeds and 60 points: $6.14M is 36% above the optimal ask of $4.50M'. At theta .75 the walk-away ask is $4.70M, where Omni is 72 and the caption says 4% an… |
| `scores:categories:size-scored-as-business-quality` | The numbers reproduce. Node, prof median profile mkT(0) at $100k, $700k, $5M and $20M: Omni and business are 50/50 at every size; Financial quality reads 37/55/71/80, Buyer attractiveness 24/50/76/87, and the category mean 47.0/51.9/56.6/58.8. But this is labelled judgment, it is display-only, and it matches the console's own buyer model. (1) The Data-tab judgment ledger lists 'Category sub-score weights, 9, the nine… |
| `scores:categories:market-position-reads-data-density` | The numbers reproduce. Node, median profile at $700k priced at bestRatio(t,0,0), against loadWith with the comps term zeroed: restaurants 47 vs 44, vet 61 vs 63, auto 59 vs 57, SaaS 62 vs 64. But this is a labelled hand-set judgment and immaterial. (1) The Data tab says the IND peer table is 'hand-set numbers... the magnitudes are invented'. It lists the table as reaching 'z-scores, category scores, buyer mix'. Categ… |
| `buyers:labels:vj-is-negotiated-price-not-value-to-buyer` | This finding was measured on the pre-fix commit 0dce8cc, and the snapshot already fixes almost all of it. `git show 0dce8cc:index.html` has 'Value to buyer' as the table header (line 4212) and on the y-axis (line 3737), 'justify paying' in the lede (line 1828) and the aria-label 'by strategic fit and expected value' (line 1829). Those are the finding's line numbers. At a6d235c, the snapshot, those strings are gone (g… |
| `buyers:strategic-cap:total-premium-exceeds-stated-40pct` | The numbers reproduce, but the claim of a contradiction does not hold. With dist, ern $1M and rev $20M at ask = V, I get V = $6,122,527, not the finding's $5.157M. The ratios match: S = $6,444,766 = 0.40V/phi, Vj/V 1.5773, and stratPrem/V 0.5773. Across 4,000 random states the maximum is 0.580 (/tmp/claude-0/r1work/skeptic-buyers/f4.js). The caption '(a buyer pays away at most 40% of value)' sits on the S_j line of e… |
| `timing:eq_ts:h-undefined-huber-multiplier` | The numbers reproduce. In node, timeMult(m,1) gives 1.0012, 1.0133 and 1.0362 at m = 1.05, 1.2 and 1.5. In Playwright, with V = 4,090,444 and ask = V*m, the page shows 248 x 1.001 = 249 d, 248 x 1.013 = 252 d and 248 x 1.036 = 257 d, with the note reading '5% / 20% / 50% above'. But no displayed number or claim is wrong, so this is not a defect. (1) The substituted equation reproduces the median exactly: t_band x tMu… |
| `risk:fitrisk:tail-severity-clamped-not-108` | The documentation the finding cites includes the clamp, so the code does exactly what its documentation says. MODELS.risk.lgd.form reads 'severity(age) = 1/(1+exp(-(b0 + b_size*(ln loan - centers.ln_loan) + b_age*(clamp(age,age_range)/12 - age_center_years)))); expected loss = ... + tail x severity(108 months)', with age_range [12,96]. Under that definition, severity(108 months) is the logistic at clamp(108) = 96 mon… |
| `presentation:hero-price:tooltip-says-capped-at-ask` | The behaviour is deliberate and documented both on the page and in AUDIT.md, and no displayed number is wrong. The 102% headroom is the intended design in AUDIT.md item #1 ('The only headroom above 100% is where IBBA's band averages above the ask (102% at $5M+)'). It is also listed under 'Known inconsistency' at AUDIT.md line 558 ('The ask ceiling still takes headroom from IBBA's $5M+ ratio (up to 2.6% above the ask)… |
| `numbers:bizscore:deep-pool-outreach-still-counted` | The numbers reproduce, but the behaviour is a deliberate, documented design choice and not an incomplete fix. Reproduction (/tmp/claude-0/r1work/skeptic-numbers/f1.js, f1b.js): with own .95 and mgt .08 the business score by buyers is 50→59, 200→61, 350→63 and 600→63, while qPct stays 0.582. Across 192 profiles the largest gain is wash 66→73. The shipped fix is exactly the fix the known finding proposed: AUDIT_FINDING… |
| `numbers:srcs:beta-500k-threshold-contradicts-interpolation` | The page already documents the interpolation, and the finding misreads the Data tab. The β values do reproduce: fitTiming β is 2.200 at $250k, 2.277 at $300k, 2.493 at $500k, 2.570 at $600k and 2.640 at $707k, and rev 1e6 / ern 2.5e5 gives Vbase $441,040 and β 2.440. However, the Data-tab paragraph the finding cites (:4773-4774) continues at :4776-4777: 'β is interpolated in ln(value) between the $250k and $707k band… |
| `datatab:selfaudit:anchor-rows-test-inert-judgment-curve` | The numbers reproduce: sizeAnchor 6.77/2.95/4.00; at $20M the fitted multiple is mfg 3.10 SDE (3.41 EBITDA), prof 3.45/4.29 and medical 2.45/2.87; medical at $3.5M is 2.45/3.43; patching BANDS changes r.anchor but leaves V, M, P_C, EVp and the Omni score unchanged. The behaviour itself is documented as deliberate, though. AUDIT.md lines 247-256 record that the self-checks were rewritten to 'test exactly what they pri… |
| `datatab:model2:equation-omits-median-calibration` | The numbers are right: fitValue gives rawPoint 3,277,007, point 3,493,348 and calib 1.0660, and log_correction runs from -0.04773 to +0.10787. But the calibration step is documented on the page, in the panel that produces the value. The §8 lede reads 'the fitted BIZCOMPS equation ... median-calibrated, then placed inside the measured residual spread'. eq_v typesets E[V/X] = $1k·P̂·c(ln P̂)·q, and eq_vs renders for th… |
| `datatab:fitted-public:lede-every-row-from-dataset` | The row in question labels itself. It carries an explicit 'judgment' badge, and its text says 'The sign is from data, the size is a labelled judgment ... stated range 0.05–0.26'. fit/README.md and the main panel do the same: the time tile title reads 'overpricing costs time, a labelled judgment, see the Data tab', and the §III caption says 'stretched by a judgment multiplier'. The task's rules state that a deliberate… |

# Round 2 (verified at commit 0f1fa9b)

Round 2 ran after the round-1 batch and the time-to-close median refit. Five new auditors covered the model's math line by line, the decision layer, a property sweep across the input space, the fitted constants against their scripts and claims, and every on-screen number against the model, with visual layout out of scope. Two verifiers checked every finding against a frozen copy of 0f1fa9b: one reproduced it independently, the other tried to refute it. A finding is confirmed only if it reproduced and was not refuted. **25 findings were raised; 16 were confirmed. They reduce to 11 distinct defects**, because three auditors found the same incomplete R1-4 fix and two auditors each found three of the others. 9 were rejected.

## Confirmed

| # | Severity | Keys | Title |
|---|---|---|---|
| R2-1 | medium | `numbers:buyers:ev-capped-but-eq_b-table-and-pays-most-uncapped`, `decisions:buyers:eq-b-ev-formula-omits-ask-ceiling`, `math:buyers:eq_b-ev-uses-vj-not-capped-price` | The R1-4 fix (buyers:ev:vj-priced-above-ask-ceiling) is incomplete: EV_j now uses the ask-capped price, but eq_b, the buyer table and 'pays most' still show the uncapped V_j, so the table's columns no longer multiply to its EV |
| R2-2 | medium | `decisions:optimize:anchoring-keeps-rising-past-rho-max-utility-card-keeps-over-cap-ask` | Past RHO_MAX the realised price keeps rising, against the documented claim that it stops, and the utility optimiser then keeps an over-cap ask that the walk-away tile rejects |
| R2-3 | medium | `fits:competition:heldout-poisson-mislabelled-same-scale` | Data tab and MODELS call the -1.702 held-out benchmark 'a Poisson at the same scale', but it is a Poisson at its own fitted scale 0.255; at the shipped 0.184 scale it scores -1.774, no better than the old 0.34 judgment |
| R2-4 | low | `fits:ttc_medians:days-on-market-self-audit-flipped-off`, `math:timing:selfaudit-days-row-flips-off-after-median-refit` | The median refit turned the 'Days on market' self-audit row from 'in range' to 'off', with no note anywhere |
| R2-5 | low | `numbers:eq_vs:hinge-definition-omits-3m-sde-cap`, `math:value:eq_vs-hinge-definition-omits-cap` | The R1-20 fix (presentation:eq_v:general-form-terms-never-valued) defines h as 'ln(SDE/$150k), floored at 0', but above $3M of SDE the code caps it, so the printed definition no longer reproduces the printed h or P-hat |
| R2-6 | low | `fits:ttc_medians:loi-leg-share-36pct-stale`, `invariants:timing:loi-share-36pct-stale-after-median-refit` | 'LOI-to-close leg (about 36% of it)' was computed with the published medians; with the fitted medians that ship, the same computation gives 40% (43% for the framework example) |
| R2-7 | low | `fits:ttc_medians:median-se-omits-month-reporting-convention` | The ± on the fitted medians is sampling-only, yet the Data tab says the ± is widened for brokers rounding or truncating months; under the truncation reading every median moves +0.53 to +0.57 months (about 3 SE) |
| R2-8 | low | `fits:datatab:nagg-omits-ibba-cash-at-close` | The aggregate tally ('30 read from published market aggregates') and the Aggregate section leave out IBBA's cash-at-close shares, which the model reads into the hero's 'cash at close' figure |
| R2-9 | low | `decisions:datatab:buyers-interv-judgment-rows-miscounted-and-reach-understated` | The judgment ledger counts BUYERS as 8×4 (12 of those are inert window edges) and leaves out its 22 live fit coefficients; INTERV is counted 33 against 43 hand-set numbers; and the BUYERS row omits that it moves P_C below a typical pool |
| R2-10 | low | `numbers:foot:timing-called-market-aggregate-after-ttc-fit` | After the post-round-1 time-to-close refit (0f1fa9b) the time tile is badged 'fitted', but the console footer still calls timing a 'market aggregate', and the Data tab still files time to close under the Aggregate section |
| R2-11 | low | `numbers:pc-lede:never-on-quality-contradicted-by-sensitivity-dpc` | The fix for closing:datatab:pc-quality-independence-claim-false-at-fixed-ask is incomplete: the console lede and the Aggregate key still say P_C never depends on business quality, while the same page's sensitivity shows owner independence moving P_C by 5.2 pts |

### R2-1. The R1-4 fix (buyers:ev:vj-priced-above-ask-ceiling) is incomplete: EV_j now uses the ask-capped price, but eq_b, the buyer table and 'pays most' still show the uncapped V_j, so the table's columns no longer multiply to its EV

- **Keys:** `numbers:buyers:ev-capped-but-eq_b-table-and-pays-most-uncapped`, `decisions:buyers:eq-b-ev-formula-omits-ask-ceiling`, `math:buyers:eq_b-ev-uses-vj-not-capped-price`  
- **Severity:** medium  
- **Where:** index.html model() lines 2973-2974 (b.Pj=softMin(b.Vj,out.ceil); b.EV=b.PE*b.PCj*b.Pj) and 2905-2906 (out.top chosen by Vj; stratPrem=top.Vj-V). render(): eq_b line 4366 (EV_j = P_E,j P_C,j V_j), buyer table lines 4358/4363 ('Price it would pay' = money(b.Vj)), eq_bs line 4371 ('pays most: ... -> V_j (+..., +...% over model value)'), drawStars labels and axis 'Price this buyer would pay'

**Why it is wrong.** Since R1-4 the model pays each buyer softMin(V_j, ceiling), because no realised price can exceed the ask ceiling. Every figure displayed around that change still uses the uncapped V_j. The equation on screen (EV_j = P_E P_C V_j) is not the one that produces the EV column, so a reader cannot rebuild Expected value from the three columns beside it (off by 1.2-1.6x at the default and up to 8x on an underpriced large deal). 'Pays most' and its '+26.8% over model value' premium describe money the model says this listing never collects. That is the half of R1-4 ('pays most' prices V_j above the ask) the fix left open, and its own proposal was to show the ask-capped figure beside 'pays most'.

**Verifier (reproduce).** Confirmed: the shipped R1-4 fix is incomplete. The printed equation eq_b is not the formula that produces the EV column. 'Pays most' and its premium still show only the uncapped V_j, with no capped figure beside them, although R1-4's own proposed fix asked for one ('would pay $5.19M; this ask caps it at $3.24M'). Showing V_j as 'Price it would pay' (willingness to pay) is defensible on its own. The genuine defects are the mismatched eq_b formula and the missing capped price in eq_bs and the table, which leave EV impossible to rebuild from the displayed columns. Not in KNOWN_FINDINGS except as the R1-4 fix this extends. Medium is reasonable given the 8x gap on underpriced large deals; low-to-medium at the default.

**Fix (as proposed).** Print eq_b as EV_j = P_E,j * P_C,j * min(V_j, ceiling), with softmin as in eq_a. Add the capped price to the table (e.g. 'Price at this ask' = money(b.Pj)) or relabel V_j 'Would pay (uncapped)'. In eq_bs, give the capped price next to 'pays most', e.g. 'would pay $5.19M; this ask caps it at $3.24M', or pick and word 'pays most' on Pj. Add a test that PE*PCj*Pj equals EV for each displayed row.

### R2-2. Past RHO_MAX the realised price keeps rising, against the documented claim that it stops, and the utility optimiser then keeps an over-cap ask that the walk-away tile rejects

- **Keys:** `decisions:optimize:anchoring-keeps-rising-past-rho-max-utility-card-keeps-over-cap-ask`  
- **Severity:** medium  
- **Where:** index.html model() l.2950-2953 (comment: 'Anchoring stops at RHO_MAX ... beyond it a higher ask only costs closing probability') and l.3034 (Pf[i]=W*anchorAt(rhoOf(s.ask/W))*comp, which caps each slice's own ask/W, not the listing's gap); AUDIT.md l.21 item #3 ('Past that point, a higher ask only costs closing probability'); optimize() l.3533 (const ru=hasR?...:r; a subset without a reprice keeps s0.ask with no bound); bestRatio() l.3290-3296 (TOP=RHO_MAX, 'a corner solution, not a recommendation'); render o_list2 / #optout

**Why it is wrong.** The code contradicts the stated mechanism. AUDIT.md #3 and the model comment say anchoring and the ceiling stop at RHO_MAX, so a higher ask beyond it 'only costs closing probability'. But anchoring is applied to each fan slice at ask/W. Every slice above the median is still below RHO_MAX when the ask reaches 1.5V, so E[P|close] keeps rising until about 2xV. That is exactly the unmeasured region bestRatio refuses to search ('a corner solution, not a recommendation'). The optimiser does not respect that domain either. Its utility search compares 'reprice to optRho' against 'keep the current ask', and the current ask is unbounded. So for any patient seller who enters an ask above the cap, the second card recommends keeping it: two recommendations for the same objective on the same page disagree ($6.14M vs $8.18M), and the card's choice rests entirely on the anchoring past RHO_MAX that the documentation says does not exist.

**Verifier (reproduce).** Confirmed and genuine. The code contradicts its documentation in three places: AUDIT.md #3 ('Anchoring and the ceiling both stop rising past RHO_MAX ... Past that point, a higher ask only costs closing probability'), the model comment at l.2950-2953 and the RHO_MAX comment ('anchoring earns nothing past it'). Only the point anchoring (anchorF, the multiple-table row, eq_a) and the ceiling stop. The per-slice anchoring at l.3034 does not, so E[P|close] rises 2% past the cap.

The bestRatio comment admits that utility 'kept climbing into that unmeasured region (a corner solution, not a recommendation)' and limits the search to RHO_MAX. But optimize() compares 'reprice to optRho' against the user's current ask with no bound. For a patient seller (theta >= ~.78) who enters an ask above the cap, the utility card therefore recommends keeping that ask, up to at least 2.29x the improved value. …

**Fix (as proposed).** Make the anchoring stop where the documentation says it stops. Cap the anchoring argument on the listing's gap, e.g. rhoOf applied to min(ask, RHO_MAX*V)/W, or equivalently W*anchorAt(rhoOf(min(ask,RHO_MAX*V)/W)), so E[P|close] is flat in the ask beyond RHO_MAX*V and U peaks inside bestRatio's domain. Independently, in optimize() treat a current ask above RHO_MAX*V' as outside the search domain: force the reprice, or clamp the kept ask to RHO_MAX*V'. Add a fuzz invariant that Vmean is non-increasing in the ask past 1.5V and that best.U never keeps an ask above RHO_MAX x its value. Update AUDIT.md #3 and the optNote 'rises all the way to the cap' wording accordingly.

### R2-3. Data tab and MODELS call the -1.702 held-out benchmark 'a Poisson at the same scale', but it is a Poisson at its own fitted scale 0.255; at the shipped 0.184 scale it scores -1.774, no better than the old 0.34 judgment

- **Keys:** `fits:competition:heldout-poisson-mislabelled-same-scale`  
- **Severity:** medium  
- **Where:** index.html Data tab 'Fitted from public data' competition row (line ~5316: 'Held-out quarters: log-likelihood ${heldout_loglik_per_deal.nb} per deal, against ${...poisson_same_scale} for a Poisson at the same scale'); MODELS.fitted.competition.heldout_loglik_per_deal.poisson_same_scale; source fit/competition_buyers.py lines 588-592 ('poisson_fitted_scale_M5P')

**Why it is wrong.** The -1.702 figure is a Poisson whose scale was refitted to 0.255, which is 39% above ENG_SHARE. 'At the same scale' tells the reader the comparison holds the 0.184 scale fixed and isolates the NB-versus-Poisson shape. The console keeps the Poisson shape at 0.184, and that combination scores -1.774 on held-out quarters, 0.186 nats behind the NB instead of 0.114. It is also no better than the old 0.34 Poisson (-1.773). The MODELS key name repeats the error.

**Verifier (reproduce).** Confirmed. In this row 'the scale' means ENG_SHARE c (the text says the NB is 'used only to calibrate the scale'). The -1.702 Poisson does not use that scale: it uses its own MLE, c=0.255, 39% higher. A Poisson actually at 0.184, which is the shape-and-scale pair the thin-pool factor uses, scores -1.774. That is 0.186 nats behind the NB (not 0.114), and marginally worse than the old 0.34 Poisson (-1.773). The NB-beats-Poisson conclusion stands either way. The defect is the label and key name. Severity: low to medium.

**Fix (as proposed).** Relabel the figure 'a Poisson at its own fitted scale (0.26)', rename the key (e.g. poisson_own_scale), and add the held-out score of the Poisson at 0.184 (-1.774) that the console actually uses, next to the old 0.34 Poisson (-1.773).

### R2-4. The median refit turned the 'Days on market' self-audit row from 'in range' to 'off', with no note anywhere

- **Keys:** `fits:ttc_medians:days-on-market-self-audit-flipped-off`, `math:timing:selfaudit-days-row-flips-off-after-median-refit`  
- **Severity:** low  
- **Where:** index.html renderCalib() row 'Days on market, main street, fairly priced' (line 5468: ms=at('prof',158950,703000), test |ms.tMed-170|<40); fitTiming TM switch (line 2445); AUDIT.md:253 ('two rows honestly read "off"') and AUDIT.md:442-444 (the follow-up says the BizBuySell days-on-market self-check must be re-verified)

**Why it is wrong.** The refit adds a third failing self-audit row. AUDIT.md still says only two rows 'honestly read off' (2.35x and 6.77x). The open follow-up this change closes explicitly required this BizBuySell days-on-market self-check to be re-verified once the medians moved. It was not, and the regression is undocumented. The fitted band median at $373k now sits 43 days above BizBuySell's 170-day median. Either the benchmark comparison (IBBA listing-to-close vs BizBuySell days on market) needs a note, or the check's target or window needs revisiting.

**Verifier (reproduce).** Confirmed. The 'off' reading itself is honest, and the self-audit is meant to show it. The defect is that the refit flipped the row from in range (206.7 d) to off (213.3 d), although the closing follow-up said explicitly that this check must be re-verified, and nothing records it. The page and the commit say nothing, AUDIT.md still lists two off rows, and no test pins the row. A one-line note fixes it, since the explanation already exists in anchoring_realization's RESULT: BizBuySell days on market (171) against IBBA listing to close (~217). So does re-targeting the benchmark. Severity: low to medium.

**Fix (as proposed).** Add a sentence to the self-audit and AUDIT.md saying the fitted medians put Main-Street listing-to-close at about 213 days against BizBuySell's 170, and why (different clocks and samples: anchoring_realization's RESULT already notes IBBA's like-for-like median is 217 days). Alternatively, re-target the row to an IBBA-consistent benchmark. Add a test that pins the row's status.

### R2-5. The R1-20 fix (presentation:eq_v:general-form-terms-never-valued) defines h as 'ln(SDE/$150k), floored at 0', but above $3M of SDE the code caps it, so the printed definition no longer reproduces the printed h or P-hat

- **Keys:** `numbers:eq_vs:hinge-definition-omits-3m-sde-cap`, `math:value:eq_vs-hinge-definition-omits-cap`  
- **Severity:** low  
- **Where:** index.html render() eq_vs line 4293 (label 'ln(SDE/$150k), floored at 0' next to r.fv.hinge); fitValue line 2138 (hinge = (hc-hk) + slope_beyond_cap*(ln sk - hc) above cap_sde_thousands = 3000)

**Why it is wrong.** R1-20 added the term definitions so that 'the substituted line can be checked against' eq_v. Above $3M of SDE, which the rail reaches easily (earnings up to 85% of revenues up to $200M), the definition printed beside h is false. A reader following it gets a value 10-20% higher than the boxed E[V|X]. The cap is a deliberate part of the fit (the multiple goes flat beyond the data), but the console never states it.

**Verifier (reproduce).** Confirmed, low. The cap is a deliberate, documented part of the fit: MODELS.value.size_hinge.form, and the Data tab Model II block prints 'then slope 0.535951 above 3M'. But the Console definition added for R1-20, whose purpose is that 'the substituted line can be checked against' eq_v, is wrong for any SDE above $3M, a value the earnings field accepts. A reader who applies it gets a P-hat 3-20% too high. The fault is incomplete console labelling, not a model bug.

**Fix (as proposed).** Print the full definition, e.g. 'h = ln(SDE/$150k) floored at 0, rising at 0.536 per log point above $3M SDE', or switch the label on r.fv.hinge when s.ern exceeds cap_sde_thousands. Add a test that the printed definition reproduces r.fv.hinge for ern in {1e5, 1.45e6, 5e6, 8e6}.

### R2-6. 'LOI-to-close leg (about 36% of it)' was computed with the published medians; with the fitted medians that ship, the same computation gives 40% (43% for the framework example)

- **Keys:** `fits:ttc_medians:loi-leg-share-36pct-stale`, `invariants:timing:loi-share-36pct-stale-after-median-refit`  
- **Severity:** low  
- **Where:** index.html Data tab 'Overpricing costs time' note (line 4919-4920, hard-coded 'about 36% of it'); timeMult comment line 2358; the derived '0.06-0.07 if only the marketing leg were stretched' (lines 2365-2366, Data tab row and note); origin fit/overpricing_time.py line 1172 LOI_SHARE = median of r.ft.loi*30.44/r.ft.days over 64 median businesses

**Why it is wrong.** The text is a hard-coded number derived from the model's band medians, and the median refit moved it from 36% to 40%. The parenthetical 'about 0.06-0.07 if only the marketing leg were stretched' rests on the same share. It is 0.09-0.10 x (1-0.36). With 0.40 it becomes 0.054-0.060, so about 0.05-0.06. The note therefore understates how much of the stretch falls on a leg the analogs do not measure.

**Verifier (reproduce).** Confirmed. The 36% was computed from the published medians that the refit replaced. With the shipped medians the same computation gives 40%, and the table beside it implies 32-43%. The derived marketing-leg figure shifts slightly, to about 0.05-0.06. The fit/README says the LOI medians feed no console figure, but this sentence is a claim about the console's own median, and it should use the medians the page now shows. Severity: low.

**Fix (as proposed).** Compute the share live, e.g. from MODELS.fitted.ttc_medians.loi/listing as overpricing_time.py defines it, or update both the comment and the Data tab to 'about 40%' and the marketing-leg equivalent to 'about 0.05-0.06'.

### R2-7. The ± on the fitted medians is sampling-only, yet the Data tab says the ± is widened for brokers rounding or truncating months; under the truncation reading every median moves +0.53 to +0.57 months (about 3 SE)

- **Keys:** `fits:ttc_medians:median-se-omits-month-reporting-convention`  
- **Severity:** low  
- **Where:** index.html Data tab Model III table (median ± listing_se, line 4866) and note ('The ± is the standard error from resampling quarters, widened because brokers may round or truncate months and because "under one month" is ambiguous', line ~4882); MODELS.fitted.ttc_medians.listing_se; fit/time_to_close_medians.py interval() (off = 0.5 only) and step 2 (quarter bootstrap only)

**Why it is wrong.** The table shows a median ± and a β ± side by side, and the only sentence that explains '±' says it is widened for the month-reporting convention. That is true for β and false for the medians. Their ± is quarter-bootstrap sampling error only, while the documented convention ambiguity shifts every median by about 3 of those SEs. The medians' uncertainty is therefore understated by about a factor of 2-3, inconsistently with the shape row beside it.

**Verifier (reproduce).** Confirmed. The sentence was written when β was the only ± in the table (the shape script's template showed the histogram medians without ±). After the refit added median ±, the sentence was left unqualified. It is true for β and false for both median columns. The convention ambiguity that the shape fit treats as a systematic term moves every median by about 0.55 months, which is 2-3 times the listing SE and much more for LOI. The 'Fitted from public data' row correctly says 'quarter-bootstrap SEs', so the page contradicts itself. Severity: low.

**Fix (as proposed).** Either add the rounding-vs-floor half-gap (about 0.27-0.28 months) in quadrature to listing_se and loi_se, as time_to_close_shape.py does for β, or label the median ± as 'sampling only (quarter bootstrap); reading months as truncated would add about 0.55 months to every median'.

### R2-8. The aggregate tally ('30 read from published market aggregates') and the Aggregate section leave out IBBA's cash-at-close shares, which the model reads into the hero's 'cash at close' figure

- **Keys:** `fits:datatab:nagg-omits-ibba-cash-at-close`  
- **Severity:** low  
- **Where:** index.html renderData() nAgg (lines 4593-4601, comment 'counted from the tables themselves' lists Pepperdine bases and gap shares, IBBA price-to-ask, BizBuySell price-to-ask, prime, Census, BLS); Aggregate section note 'Three more published aggregates feed the console' (line ~4818); model() lines 3072-3074 read MODELS.close_and_timing.ibba_cash_at_close.by_band

**Why it is wrong.** The tally claims to count the published aggregates the console reads, from the tables themselves. A five-value IBBA table that sets a displayed dollar figure ($347k deferred out of $2.10M on the default inputs) is missing. So the aggregate count is 5 short, and the Aggregate section's list of feeding aggregates is incomplete.

**Verifier (reproduce).** Confirmed. A five-value IBBA aggregate that sets displayed dollar figures ($347k deferred out of $2.10M on the default inputs) is missing from the aggregate tally and from the Aggregate section's list of feeding aggregates. Commit 0f1fa9b says 'the aggregate count is read from the tables', so this is an omission in that computed count (30 where it should be 35). Severity: low.

**Fix (as proposed).** Add C.ibba_cash_at_close.by_band.length to nAgg (35), and list IBBA's cash at close in the Aggregate section's 'more published aggregates' sentence.

### R2-9. The judgment ledger counts BUYERS as 8×4 (12 of those are inert window edges) and leaves out its 22 live fit coefficients; INTERV is counted 33 against 43 hand-set numbers; and the BUYERS row omits that it moves P_C below a typical pool

- **Keys:** `decisions:datatab:buyers-interv-judgment-rows-miscounted-and-reach-understated`  
- **Severity:** low  
- **Where:** index.html renderData() nJudg l.4587-4592 (BUYERS.length*4 + INTERV.length*3); judgment table rows l.5133-5136 (BUYERS count ${BUYERS.length*4}, reach 'Pursue-first, strategic premium, competitive tension'; INTERV count ${INTERV.length*3}); model() sizeFit (lo/hi read only when BUYER_GROUP has no group: eta, mbo); peRef → nEngRef/nPool → thinF

**Why it is wrong.** The ledger exists to say how many hand-set numbers there are and which reported figures they reach (R1-31/R1-32 fixed the same kind of miscount elsewhere). The BUYERS count includes 12 numbers the model never reads and leaves out the 22 coefficients that set engagement, pursue-first, the competition premium and the typical pool's engagement (peRef). INTERV is undercounted by 10 (30%). Through peRef the archetypes set the thin-pool factor, so below a typical pool they move the closing probability, expected proceeds and the Omni score. The IND row says this about IND buyers, but the BUYERS row lists only pursue-first, strategic premium and competitive tension.

**Verifier (reproduce).** Confirmed. This is the same kind of ledger miscount that was accepted and fixed in R1-32 (counting non-parameters) and R1-31 (omitting live parameters). BUYERS*4 counts 12 numbers the model never reads and omits the 22 fit-function coefficients. Those coefficients set engagement, pursue-first, the competition premium and peRef; the code's own ENG_SHARE comment says to refit 'whenever ... the BUYERS fit functions, peRef ... change'. INTERV*3 undercounts the hand-set days, cost and effect numbers by 10 (43 against 33).

The BUYERS reach column omits that the archetypes move P_C, EVp and the Omni score below a typical pool through peRef and thinF, which the IND row states for IND buyers. A window change can move PC below a typical pool and leave the $1.45M calibration point unchanged, so a one-scalar ENG_SHARE refit cannot absorb it.

Caveat: the ledger counts loosely elsewhere too (e.g. …

**Fix (as proposed).** Count BUYERS as syn + mf (16) + the eta/mbo windows (4) + the 22 fit coefficients (+ the PE/PCj form constants if they are meant to be counted), and INTERV as the actual days, cost and effect parameters (43), or compute both from the definitions. Add to the BUYERS row: 'and, through the typical pool's engagement, the thin-pool factor: the closing probability, expected proceeds and Omni score below a typical pool'.

### R2-10. After the post-round-1 time-to-close refit (0f1fa9b) the time tile is badged 'fitted', but the console footer still calls timing a 'market aggregate', and the Data tab still files time to close under the Aggregate section

- **Keys:** `numbers:foot:timing-called-market-aggregate-after-ttc-fit`  
- **Severity:** low  
- **Where:** index.html footer line 5566 ('closing probability and timing are market aggregates conditioning on deal size and price gap'); Data tab Aggregate section header line 4811 ('closing probability & time to close'), with the Model III fitted-median table placed inside it (line 4861); compare o_t_pv in render() lines 4185-4188 (class 'f', 'fitted') and the srcs 'fitted Time to close' item (line 5537)

**Why it is wrong.** Since 0f1fa9b the band medians and the shape are both fitted: MODELS.fitted.ttc_medians from fit/time_to_close_medians.py, MODELS.fitted.ttc_shape. The console's own badge and source note say 'fitted', while the footer and the Data tab's tier heading still describe timing as a published aggregate. The page's provenance labels contradict each other on the same quantity.

**Verifier (reproduce).** Confirmed, low. The footer's provenance claim for timing contradicts the 'fitted' badge and Method item on the same page, a stale label left by the 0f1fa9b refit. The Data-tab half is weaker: the Model III subsection inside the Aggregate section explicitly says both are fitted, and its table includes the aggregate Price/ask column, so placing it there is partly defensible. Only the section ref and lede still imply that time to close is a published aggregate. The footer is the clear defect.

**Fix (as proposed).** Footer: 'closing probability is a market aggregate conditioning on deal size, price gap and, below a typical pool, the buyers contacted; time to close is fitted to IBBA's histograms, with a labelled judgment factor for time above value'. Change the Aggregate section's ref to 'closing probability' and move the Model III table to the Fitted section, or say there that it is fitted.

### R2-11. The fix for closing:datatab:pc-quality-independence-claim-false-at-fixed-ask is incomplete: the console lede and the Aggregate key still say P_C never depends on business quality, while the same page's sensitivity shows owner independence moving P_C by 5.2 pts

- **Keys:** `numbers:pc-lede:never-on-quality-contradicted-by-sensitivity-dpc`  
- **Severity:** low  
- **Where:** index.html console Probability-of-closing lede line 1791 ('it conditions on deal size, the asking gap and the number of buyers contacted, never on business quality'); Method-panel key line 5499 ('Aggregate ... - not on business quality'); compare the corrected Method-panel item ('At the same dollar ask, a better business has a smaller price gap and so closes more often') and eq_ds / the sensP bars

**Why it is wrong.** Round 0 rewrote only the Data-tab sentence. P_C reads the gap to the quality-positioned V, so at any fixed dollar ask above value, every quality input moves P_C. The console's own sensitivity panel prints exactly that (+5.2 pts per sd of owner independence) beneath a lede that says the probability conditions 'never on business quality'. The accurate statement, true at a fixed ask relative to model value, already appears in the Method panel on the same tab.

**Verifier (reproduce).** Confirmed, low: the round-0 fix (#4, closing:datatab:pc-quality-independence-claim-false-at-fixed-ask) is incomplete. That finding's Where named only the Data-tab provenance sentence, which was reworded. The same absolute claim survives in the console lede (line 1791) and the Aggregate key (line 5499). On the same page, the sensitivity panel shows quality moving P_C by up to 5.2 pts at an ask above value. A reader could take 'never on business quality' as a statement about conditioning variables, since quality enters only through the gap. But read as a statement about the function it is false, and the page's own Method item already gives the accurate wording.

**Fix (as proposed).** Reword both, e.g. 'it has no quality term: at the same ask relative to model value, quality does not move it; at the same dollar ask, a better business has a smaller gap and closes more often'.

## Rejected by verification

| Key | Why rejected |
|---|---|
| `math:risk:loan-sized-on-model-value-exceeds-ask` | The numbers reproduce (/tmp/claude-0/r2work/skeptic-math/f1.js, f1b.js). At the default, V is 4,090,444, ceil 3,240,000, Vmean 3,103,307 and risk.loan 3,476,877, which is 1.073x the ask. p is 3.178% and rel 0.563. fitRisk(min(V,ceil)) gives 3.739%, and p stays 3.178% at ask/V of 0.5, 0.79, 1.0 and 1.2. The behaviour is still intended, labelled on the page, and immaterial to any decision.  (1) The page states the … |
| `decisions:buyers:synergy-captured-column-shows-buyer-synergy-not-seller-share` | Refuted: this re-raises a point that was already rejected, adds no new evidence against the rejection, and is immaterial.  The numbers reproduce. Direct strategic S is 1,101,013 and φS is 418,385. Vj−V is 1,097,907, and the row reads '$1.10M $5.19M $967k'.  However, round-1 finding buyers:labels:vj-is-negotiated-price-not-value-to-buyer (KNOWN_FINDINGS, rejected) already covered exactly this. Its reproduction in … |
| `invariants:selfaudit:days-on-market-row-off-after-median-refit` | The numbers reproduce, but the behaviour is correct, it was anticipated in the record, and it is immaterial.  Reproduction: /tmp/claude-0/r2work/invariants/selfaudit_days.js gives tMed 213.29 days with the fitted medians and 206.67 with TM=null. pw2.js shows three rows reading 'off' (2.35x, 213 days, 6.77x).  (1) The row does what the live self-audit is designed to do. The section says 'These run live against the … |
| `invariants:fuzz:rate-fixture-pins-risk-at-spread-cap` | The fixture facts reproduce: fuzzrate.js shows all 1,500 of 1,500 fuzz samples at spread 3.0, and the framework example gives 3.18% on the page path against 7.83% at rate 10.5. But the central claim is contradicted by the test suite. The finding says the size-dependent spread the page uses, and its interaction with loan size in the risk headline, 'sit outside every risk invariant'. They do not: - tests/model.test.js … |
| `invariants:value:soi-wedge-monotone-claim-contradicted` | The numbers reproduce, but the defect is immaterial: no displayed number or claim is wrong and no decision changes. wedge.js confirms the knots 1.8679 / 1.8978 / 1.8117 / ... / 1.1199, and sdeEbitdaWedge('62') reads 1.9158 at $158k, 1.9463 at $354k and 1.9023 at $500k.  (1) The monotone '1.90 to 1.08' claim exists only in a source comment (index.html:2088-2091) and in MODELS.value.soi_size_wedge.why. The 'why' … |
| `fits:ttc_medians:shrink-weight-mislabelled-and-oos-scores-unshrunk` | Refuted as immaterial. The code reading is right: eb_line's B=v/(v+tau2) is the weight on the line, yet RESULT stores 1-B as 'shrink_weight_on_line'. But that field exists only in /tmp/claude-0/fit5/time_to_close_medians/RESULT.json. Nothing in index.html, fit/README.md, the tests or AUDIT reads it (grep finds it only at the script's line 194). The shrunk medians are computed correctly from B. On the held-out claim, … |
| `fits:ttc_shape:hist-median-5-50m-double-rounded` | Refuted as immaterial. The arithmetic holds: fits.json band_table 5M-50M listing grouped_median is 9.951368; round(x,2)=9.95 and '%.1f'%9.95 = '9.9', where a single rounding gives 10.0. But 9.9 is only 0.051 months from the true 9.951, which is 0.001 months (about 1 hour) beyond the 0.05 half-unit tolerance. The value is a boundary tie on a display-only constant (the ttc_shape comment says 'hist_* are the … |
| `numbers:eq_cs:fitted-residual-band-recentred-on-quality-value` | The numbers reproduce: the default band is $2.09M-$6.93M, which is r.V x 0.5102/1.694. r.vLo/vHi = $1.78M/$5.92M, and qFactor = 1.171. But the centring is the model's documented design, not a mislabel. (1) AUDIT.md lines 52-55 record it as a known, deliberate limitation: 'Quality positioning moves the median, and the full residual fan is then applied around it. If quality really explains part of the residual, the … |
| `numbers:selfaudit:days-on-market-row-off-after-ttc-refit` | The numbers reproduce. For the renderCalib ms profile (prof, $158,950 SDE, $703k revenue, ask = V, Vbase $373,423), tMed is 206.7 d at r1snap and 213.3 d at r2snap, and the Data tab reads '213 days vs 170 +/- 40 days off'. But it is not a defect. The row computes exactly what its label says and reports a true verdict. No displayed number or claim is wrong, and no decision depends on it. The page's design accepts … |

Two of the rejected findings concern `fit/time_to_close_medians.py` and were rejected only as immaterial: the RESULT field `shrink_weight_on_line` stored the weight on each band's own estimate, and the out-of-sample scores were computed for the raw maximum-likelihood medians rather than the shrunk medians that ship. Both are corrected in the round-2 batch anyway, since the script is new.
