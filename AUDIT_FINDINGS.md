# Audit findings: logic audit, ultracode round

These are the 25 defects that adversarial verifiers confirmed, each with a numeric reproduction, in the Phase 3 logic audit of `index.html` at commit 7cac297. Severity: 9 medium, 16 low. None were rated high.

Several findings were raised independently by different auditors and describe the same defect. They are listed separately, as confirmed, and fixed once. Overlapping groups:

- **A. Intervention table: closing probability is not constant across rows:** #3, #12, #17
- **B. Delay cost charged on the median but labelled E[T]:** #6, #13, #19
- **C. Optimiser U card: "different programme / less time and spend":** #11, #15
- **D. optNote lower branch: net gain shown as the value of time:** #14, #18
- **E. Closing-probability equation omits the tail, thin pool, size base and floor:** #5, #25, #16

The rest stand alone: #1, #2, #4, #7, #8, #9, #10, #20, #21, #22, #23, #24.

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
