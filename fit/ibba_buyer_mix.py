"""Build IBBA buyer-mix table from hand-read passages of the Market Pulse texts."""
import csv, json, statistics as st
P = "ibba-market-pulse__"
F = dict(
 q212=P+"MARKETPULSE-Q2.txt", q312=P+"MARKETPULSE-Q3.txt", q412=P+"IBBA-MARKETPULSE-Q4.txt",
 q113=P+"IBBA-MARKETPULSE-Q1-13.txt", q213=P+"Q2-Market-Pulse-Report.txt", q413=P+"2013-Q4-MARKETPULSE.txt",
 q214=P+"2014Q2MARKETPULSE.txt", q314=P+"2014marketpulse-Q3.txt",
 q115=P+"IBBAQ12015MarketPulseExecutiveSummary.txt", q215=P+"IBBA-MarketPulse-Q2-2015-ExecutiveSummary.txt",
 q415=P+"Market-Pulse-Q4-2015-Executive-Summary.txt", q116=P+"Market-Pulse-Executive-Summary-Q1-2016.txt",
 q216=P+"Q2-2016-Market-Pulse-Executive-Summary.txt", q316=P+"Q3-2016-Market-Pulse-Executive-Summary.txt",
 q416=P+"IBBA_Q4_2016-Executive-Summary.txt", q117=P+"IBBA-Q1-2017-Executive-Summary.txt",
 q217=P+"IBBA_Q2_2017-v2.txt", q317=P+"IBBA_Q3_2017_1127-FINAL.txt", q417=P+"IBBA_Q4_2017_0222-2.txt",
 q118=P+"IBBA_Q1_2018_final01.txt", q218=P+"2018-q2-ibba.txt", q318=P+"IBBA_Q3_2018-Executive-Report.txt",
 q418=P+"IBBA_Q4_2018_Final_Executive-Summary.txt", q119=P+"2019-ibba-q1.txt",
 q219=P+"Market-Pulse_Q2_2019_ExecutiveSummary.txt", q319=P+"MarketPulse_Q3_2019_ExecutiveSummary.txt",
 q419=P+"MarketPulse-report-Q4_2019.txt", q120=P+"marketpulse-q1-2020-summary.txt",
 q220=P+"marketpulse-q2-2020-summary.txt", q420=P+"Market-Pulse-Q4-2020-ER.txt",
 q121=P+"IBBA_Q1_2021_Final_Executive-Summary.txt", q421=P+"MP_ExecutiveReport_Q4_2021.txt",
 q122=P+"IBBA_Q1_2022_Executive-Report.txt", q222c=P+"FULL_MP_Q2_2022_comp.txt",
 q322=P+"MP_Q3_2022_ExecRep.txt", q422=P+"ibba-q4-2022-market-pulse-execsum.txt",
 q123=P+"ibba_q1_2023_executive_report.txt", q223=P+"q2-2023-executive-report.txt",
 q323=P+"mp_q3_2023_executive-report.txt", q423=P+"mp_q4_2023_executive-report.txt",
)
T3="top-3 list; unlisted types censored"; T2="top-2 list; unlisted types censored"
rows=[]
def r(f,per,band,ft=None,se=None,stg=None,pe=None,oth=None,ind=None,note="",cm=()):
    rows.append(dict(report_file=F[f],period=per,band=band,first_time=ft,serial=se,strategic=stg,pe=pe,other=oth,individual=ind,note=note,cm=set(cm)))
# 2012Q2
r("q212","2012Q2","<500K",58,33,ind=91,note="text: 91% individuals; 58% first-time and 33% previous owners (58+33=91 so read as shares of all buyers). Text also gives $1MM-$5MM combined: ~50% individual, ~40% company, 10% PE (non-standard band, not tabulated)")
r("q213","2012Q2","2M-5M",ind=50,note="from Q2 2013 report: individuals (incl. past owners) were 50% of $2-5MM deals in Q2 2012")
r("q212","2012Q2","5M-50M",0,0,31,62,ind=0,note="'$5MM-plus'; text: no individual buyers, 31% other companies, 62% PE")
# 2012Q3
r("q312","2012Q3","MainStreet",ind=75,note="text: Main Street buyers 75% individuals; 60% OF INDIVIDUALS were first-time (~45% of all) - first_time left blank")
r("q312","2012Q3","5M-50M",pe=68,note="'$5million and above'; PE nearly all add-ons (one platform)")
# 2012Q4 top-2
r("q412","2012Q4","<500K",55,31,note=T2)
r("q412","2012Q4","500K-1M",40,43,note=T2)
r("q412","2012Q4","1M-2M",se=34,stg=41,note=T2)
r("q412","2012Q4","2M-5M",se=24,stg=48,note=T2)
r("q412","2012Q4","5M-50M",se=16,stg=56,pe=20,note="'$5MM+'; top-2 table + text says prior owners 3rd at 16%")
# 2013Q1 top-2
r("q113","2013Q1","<500K",47,43,note=T2)
r("q113","2013Q1","500K-1M",38,31,note=T2)
r("q113","2013Q1","1M-2M",36,stg=21,note=T2)
r("q113","2013Q1","2M-5M",40,pe=40,note=T2+"; pe = PE add-on only (platform not reported)")
r("q113","2013Q1","5M-50M",stg=40,pe=50,note="text: existing 40, PE platform 30, PE add-on 20 (pe=50)")
# 2013Q2 top-2
r("q213","2013Q2","<500K",55,33,note=T2+"; #1 labelled 'Individual' vs #2 'Past Bus. Owner' - first_time is an interpretation",cm=("first_time",))
r("q213","2013Q2","500K-1M",se=29,stg=36,note=T2)
r("q213","2013Q2","1M-2M",se=31,stg=42,note=T2)
r("q213","2013Q2","2M-5M",stg=60,ind=26,note="existing 60%, #2 a '3 way tie'; text: individuals (incl. past owners) 26%")
r("q213","2013Q2","5M-50M",stg=50,pe=21,note=T2+"; pe = PE platform only")
# 2013Q4 top-2
for b,i,s in [("<500K",85,15),("500K-1M",70,30),("1M-2M",73,18),("2M-5M",47,41)]:
    r("q413","2013Q4",b,stg=s,ind=i,note=T2+"; individual not split first/serial")
r("q413","2013Q4","5M-50M",stg=35,pe=60,note=T2)
# 2014
r("q214","2014Q2","5M-50M",pe=50,note="text only (Figure 8 not extracted): PE 'dominated 50% of purchases' in $5-50MM")
r("q314","2014Q3","<500K",47.5,39,13.5,note="Figure 8 text table with blank cells dropped; 3 values (sum 100) mapped left-to-right",cm=("first_time","serial","strategic"))
r("q314","2014Q3","500K-1M",32.3,41.9,22.6,note="Figure 8 text table with blank cells dropped (sum 96.8, one ~3.2% cell lost); mapped left-to-right",cm=("first_time","serial","strategic"))
r("q314","2014Q3","1M-2M",12.9,51.6,19.4,16.2,note="all 5 columns present: PE platform 6.5 + add-on 9.7")
r("q314","2014Q3","2M-5M",note="UNMAPPED: 4 of 5 columns present (22.2, 11.1, 44.4, 22.2); column alignment lost")
r("q314","2014Q3","5M-50M",note="UNMAPPED: 4 of 5 columns present (10, 40, 30, 20); column alignment lost")
# 2015Q1
r("q115","2015Q1","<500K",46,31,24,note="full Main Street table (3 types listed, sum 101)")
r("q115","2015Q1","500K-1M",50,23,27,note="full Main Street table (3 types listed, sum 100)")
r("q115","2015Q1","1M-2M",40,36,20,note="full Main Street table (3 types listed, sum 96)")
r("q115","2015Q1","2M-5M",12.5,37.5,25,12.5,note="top list: serial 37.5, existing 25, PE platform 12.5 & 1st-time 12.5 tie (sum 87.5); pe = platform only")
r("q115","2015Q1","5M-50M",0,0,25,50,25,ind=0,note="PE add-on 50, existing 25, other 25 (sum 100 -> individuals implied 0)")
# 2015Q2
r("q215","2015Q2","<500K",57,23,19,note="full Main Street table (sum 99)")
r("q215","2015Q2","500K-1M",49,23,28,note="full Main Street table (sum 100)")
r("q215","2015Q2","1M-2M",44,34,19,note="full Main Street table (sum 97)")
r("q215","2015Q2","2M-5M",20,24,36,note=T3)
r("q215","2015Q2","5M-50M",stg=38,pe=50,note=T3+": existing 38, PE platform 38, PE add-on 12 (pe=50)")
# 2015Q4 garbled pies
r("q415","2015Q4","<500K",53,28,17,0,2,note="text: first-time largest, PE not active (0). Pie numbers 53/28/17/2 garbled; serial/strategic/other mapped by label order",cm=("serial","strategic","other"))
r("q415","2015Q4","5M-50M",7,7,33,48,4,ind=14,note="text: individuals 14% (7 first,7 repeat), PE largest (48). Pie numbers 33/4 mapped to existing/other by label order",cm=("strategic","other"))
# 2016Q1
r("q116","2016Q1","<500K",43,40,14,note="text: first-time largest. Pie 43/40/14/3 garbled; serial/strategic by label order; 3% is PE or other (unassigned)",cm=("serial","strategic"))
r("q116","2016Q1","5M-50M",10,5,33,43,10,ind=15,note="text: individuals 15% (10 first, 5 repeat), PE largest (43). Pie 33/10 mapped to existing/other by label order",cm=("strategic","other"))
# 2016Q2
r("q216","2016Q2","<500K",42,40,12,note="text: first-time largest. Pie 42/40/12/4/2 garbled; serial/strategic by label order; 4/2 = PE/other (unassigned)",cm=("serial","strategic"))
r("q216","2016Q2","5M-50M",13,4,30,39,13,ind=17,note="text: individuals 17% (13 first, 4 repeat); PE 22 platform + 17 add-on labelled on pie; 30/13 mapped to existing/other",cm=("strategic","other"))
# 2016Q3
r("q316","2016Q3","<500K",42,40,12,note="first-time largest (42). Pie 40/12/2/4 garbled; serial/strategic by label order; 2/4 = PE/other (unassigned)",cm=("serial","strategic"))
r("q316","2016Q3","5M-50M",0,12.5,25,50,12.5,ind=12.5,note="text: individuals 12.5% all repeat owners, no first-time; PE 'double' existing -> 50/25 pair on pie; other = remainder 12.5")
# 2016 annual
r("q416","2016ANN","MainStreet",41,35,20,2,3,ind=76,note="full-year 2016. text: 20% existing, individuals = 41 first + 35 serial; pie 76/20/2/3, PE/other by label order",cm=("pe","other"))
r("q416","2016ANN","LMM",18,15,35,23,9,ind=33,note="full-year 2016. text: individuals 18 first + 15 serial; PE 13 platform + 10 add-on; 35/9 mapped existing/other by magnitude",cm=("strategic","other"))
# 2017
r("q117","2017Q1","<500K",50,34,note=T2)
r("q117","2017Q1","500K-1M",46,22,26,note=T3)
r("q117","2017Q1","1M-2M",38,32,26,note=T3)
r("q117","2017Q1","2M-5M",24,stg=29,pe=24,note=T3)
r("q117","2017Q1","5M-50M",stg=38,pe=38,note=T2)
r("q217","2017Q2","<500K",59,26,15,1,note="text: first-time 59%. Pie 26/15/1 mapped to experienced/existing/PE-platform by label order",cm=("serial","strategic","pe"))
r("q217","2017Q2","5M-50M",13,13,27,40,ind=26,note="text: PE 40% largest, individuals 26% half repeat. Pie 20/20/13/13/27 -> PE platform 20 + add-on 20, existing 27 (sum 93)")
r("q317","2017Q3","MainStreet",48,33,18,1,note="text: first-time 48%. Pie 33/18/1 mapped by label order",cm=("serial","strategic","pe"))
r("q317","2017Q3","LMM",se=24,stg=51,note="text: existing 51, experienced owners 24. Remaining pie values 17/5/2 = first-time / PE platform / PE add-on (unassigned)")
r("q417","2017ANN","MainStreet",stg=28,oth=1,ind=71,note="full-year 2017; pie labels Individual/Existing/Other 71/28/1; 'minimal PE'")
r("q417","2017ANN","LMM",stg=38,pe=18,oth=3,ind=40,note="full-year 2017; text PE 18%; pie 38/40 mapped existing/individual by label order, other 3 remainder",cm=("strategic","individual","other"))
# 2018
r("q118","2018Q1","<500K",50,31,17,note=T3)
r("q118","2018Q1","500K-1M",32,37,24,note=T3)
r("q118","2018Q1","1M-2M",24,27,42,note=T3)
r("q118","2018Q1","2M-5M",25,20,40,note=T3)
r("q118","2018Q1","5M-50M",stg=37,pe=58,note=T3+": existing 37, PE platform 32, PE add-on 26 (pe=58)")
r("q218","2018Q2","<500K",49,32,17,note=T3)
r("q218","2018Q2","500K-1M",51,29,15,note=T3)
r("q218","2018Q2","1M-2M",32,29,32,note=T3)
r("q218","2018Q2","2M-5M",30,17,33,note=T3)
r("q218","2018Q2","5M-50M",13,stg=50,pe=26,note=T3)
r("q318","2018Q3","<500K",50,36,13,note=T3)
r("q318","2018Q3","500K-1M",33,42,23,note=T3)
r("q318","2018Q3","1M-2M",32,29,32,note=T3)
r("q318","2018Q3","2M-5M",26,37,30,note=T3)
r("q318","2018Q3","5M-50M",stg=20,pe=53,note=T2)
r("q418","2018ANN","MainStreet",stg=20,pe=1,oth=1,ind=78,note="full-year 2018; pie 78/20/1/1 (text says existing 22%)")
r("q418","2018ANN","LMM",stg=34,pe=25,oth=6,ind=34,note="full-year 2018; pie 34/34/25/6; text PE 25%")
# 2019
r("q119","2019Q1","<500K",49,30,19,note=T3)
r("q119","2019Q1","500K-1M",42,19,33,note=T3)
r("q119","2019Q1","1M-2M",21,34,34,note=T3)
r("q119","2019Q1","2M-5M",25,15,45,note=T3)
r("q119","2019Q1","5M-50M",stg=36,pe=48,note=T3+": existing 36, PE platform 19, PE add-on 29 (pe=48)")
r("q219","2019Q2","<500K",48,32,18,note=T3)
r("q219","2019Q2","500K-1M",27,49,20,note=T3)
r("q219","2019Q2","1M-2M",31,31,29,note=T3)
r("q219","2019Q2","2M-5M",31,38,31,note=T3)
r("q219","2019Q2","5M-50M",se=8,stg=54,pe=31,note=T3)
r("q319","2019Q3","<500K",46,34,20,note=T3)
r("q319","2019Q3","500K-1M",43,28,30,note=T3)
r("q319","2019Q3","1M-2M",44,26,21,note=T3)
r("q319","2019Q3","2M-5M",47,stg=41,note=T2)
r("q319","2019Q3","5M-50M",stg=44,pe=44,note=T2)
r("q419","2019ANN","MainStreet",43,31,23,oth=1,ind=74,note="full-year 2019; PE platform 1% + PE add-on garbled ('12%' impossible: other parts sum 99) -> pe blank")
r("q419","2019ANN","LMM",18,13,40,25,4,ind=31,note="full-year 2019; PE platform 13 + add-on 12; matches Q4-2022 4-yr series")
# 2020
r("q120","2020Q1","<500K",51,25,22,note=T3)
r("q120","2020Q1","500K-1M",48,22,28,note=T3)
r("q120","2020Q1","1M-2M",40,33,note=T2)
r("q120","2020Q1","2M-5M",37,stg=37,note=T2)
r("q120","2020Q1","5M-50M",se=20,stg=40,pe=33,note=T3+"; pe = PE add-on only")
r("q220","2020Q2","<500K",45,30,20,note=T3)
r("q220","2020Q2","500K-1M",42,29,29,note=T3)
r("q220","2020Q2","1M-2M",40,33,note=T2+"; identical to Q1 2020 text (possible copy-over)")
r("q220","2020Q2","2M-5M",40,27,note=T2)
r("q220","2020Q2","5M-50M",stg=13,pe=67,note=T3+": PE platform 40, add-on 27, existing 13")
r("q420","2020ANN","MainStreet",44,29,24,1,2,ind=73,note="full-year 2020 pie (PE = add-on 1)")
r("q420","2020ANN","LMM",22,18,33,22,4,ind=40,note="full-year 2020 pie (PE platform 11 + add-on 11)")
# 2021
r("q121","2021Q1","<500K",39,34,25,note=T3)
r("q121","2021Q1","500K-1M",37,27,30,note=T3)
r("q121","2021Q1","1M-2M",27,29,note=T2)
r("q121","2021Q1","2M-5M",36,28,24,note=T3)
r("q121","2021Q1","5M-50M",stg=20,pe=53,note=T3+": PE platform 33, existing 20, PE add-on 20")
r("q222c","2021Q2","<500K",50,28,22,0,1,note="full distribution (Q2 2022 full report, prior-year column); exec summary Q2 2021 top-3 agrees")
r("q222c","2021Q2","500K-1M",39,28,33,0,0,note="full distribution (Q2 2022 full report, prior-year column)")
r("q222c","2021Q2","1M-2M",34,31,31,3,note="full distribution (Q2 2022 full report, prior-year column); no 'other' bar")
r("q222c","2021Q2","2M-5M",12,24,44,20,0,note="full distribution (Q2 2022 full report, prior-year column)")
r("q222c","2021Q2","5M-50M",21,7,43,28,0,note="full distribution (Q2 2022 full report, prior-year column): PE platform 14 + add-on 14")
r("q422","2021ANN","MainStreet",40,31,26,ind=74,note="full-year 2021 from Q4-2022 4-yr series; Q4-2021 report text says individuals 74% (40+31) - internally inconsistent")
r("q422","2021ANN","LMM",17,17,40,24,note="full-year 2021 from Q4-2022 4-yr series; Q4-2021 report text: existing 40%")
# 2022
r("q122","2022Q1","<500K",40,44,note=T2)
r("q122","2022Q1","500K-1M",41,32,24,note=T3)
r("q122","2022Q1","1M-2M",34,20,40,note=T3)
r("q122","2022Q1","2M-5M",19,19,44,note=T3)
r("q122","2022Q1","5M-50M",15,stg=45,pe=25,note=T3+"; pe = PE add-on only")
r("q222c","2022Q2","<500K",41,38,19,1,1,note="full distribution (Q2 2022 full report)")
r("q222c","2022Q2","500K-1M",38,30,25,4,4,note="full distribution (Q2 2022 full report)")
r("q222c","2022Q2","1M-2M",37,31,31,0,note="full distribution (Q2 2022 full report); exec report's $1-2MM bullet is a copy of $2-5MM")
r("q222c","2022Q2","2M-5M",29,9,51,9,3,note="full distribution (Q2 2022 full report): PE platform 3 + add-on 6")
r("q222c","2022Q2","5M-50M",10,0,43,43,5,note="full distribution (Q2 2022 full report): PE platform 24 + add-on 19")
r("q322","2022Q3","<500K",44,33,note=T2)
r("q322","2022Q3","500K-1M",39,33,25,note=T3)
r("q322","2022Q3","1M-2M",24,40,32,note=T3)
r("q322","2022Q3","2M-5M",23,26,37,note=T3)
r("q322","2022Q3","5M-50M",stg=40,pe=31,note=T3+": PE add-on 17 + platform 14")
r("q422","2022ANN","MainStreet",39,36,23,note="full-year 2022 (4-yr series chart + text); PE/other not legible")
r("q422","2022ANN","LMM",18,17,38,24,ind=35,note="full-year 2022 (4-yr series chart + text)")
# 2023
r("q123","2023Q1","<500K",44,38,note=T2)
r("q123","2023Q1","500K-1M",47,24,22,note=T3)
r("q123","2023Q1","1M-2M",25,30,41,note=T3)
r("q123","2023Q1","2M-5M",18,27,37,note=T3)
r("q123","2023Q1","5M-50M",14,stg=57,pe=14,note=T3+"; pe = PE add-on only")
r("q223","2023Q2","<500K",47,37,note=T2)
r("q223","2023Q2","500K-1M",45,30,24,note=T3)
r("q223","2023Q2","1M-2M",29,33,31,note=T3)
r("q223","2023Q2","2M-5M",23,30,33,note=T3)
r("q223","2023Q2","5M-50M",stg=39,pe=39,note=T3+": PE add-on 22 + platform 17")
r("q323","2023Q3","<500K",49,32,note=T2)
r("q323","2023Q3","500K-1M",43,36,17,note=T3)
r("q323","2023Q3","1M-2M",43,28,25,note=T3)
r("q323","2023Q3","2M-5M",24,17,46,note=T3)
r("q323","2023Q3","5M-50M",stg=44,pe=33,note=T2+"; pe = PE add-on only")
r("q423","2023ANN","MainStreet",44,35,note="full-year 2023 text")
r("q423","2023ANN","LMM",17,19,pe=23,ind=36,note="full-year 2023 text")

TYPES=["first_time","serial","strategic","pe","other"]
# fill individual from first+serial when both stated
for x in rows:
    if x["individual"] is None and x["first_time"] is not None and x["serial"] is not None:
        x["individual"]=round(x["first_time"]+x["serial"],1); x["cm"] |= ({"individual"} if ({"first_time","serial"}&x["cm"]) else set())
    if x["cm"]:
        x["note"]+=f" [chart-mapped (excluded from summary): {','.join(sorted(x['cm']))}]"
def fmt(v): return "" if v is None else (int(v) if float(v).is_integer() else v)
cols=["report_file","period","band"]+TYPES+["individual","note"]
with open("/tmp/claude-0/fit/ibba/buyer_mix.csv","w",newline="") as fh:
    w=csv.writer(fh); w.writerow(cols)
    for x in rows: w.writerow([x[c] if c in("report_file","period","band","note") else fmt(x[c]) for c in cols])

BANDS=["<500K","500K-1M","1M-2M","2M-5M","5M-50M","MainStreet","LMM"]
def val(x,k): return None if (x[k] is None or k in x["cm"]) else x[k]
summ={"_method":{
 "type_means":"mean of stated values per band (chart-mapped/ambiguous values excluded); n = observations. Top-2/top-3 lists censor unlisted (smaller) types, so means of rarely-listed types (pe, other, and strategic/serial in small bands) are biased UP conditional on being listed and the type-mean vector does not sum to 100.",
 "pooled_strict":"per row, individual = first_time+serial (or stated individual total), strategic, financial = pe+other; only rows where all needed parts are stated; mean over those rows.",
 "pooled_complete_rows":"rows whose stated shares sum to >=95% (unlisted types treated as 0, all three groups then available), normalized to 100, then averaged."}}
for b in BANDS:
    R=[x for x in rows if x["band"]==b]
    d={"n_rows":len(R),"type_means":{}}
    for k in TYPES+["individual"]:
        v=[val(x,k) for x in R if val(x,k) is not None]
        d["type_means"][k]={"mean":round(st.mean(v),1) if v else None,"n":len(v)}
    g={"individual":[], "strategic":[], "financial":[]}
    comp=[]
    for x in R:
        ind=val(x,"individual")
        if ind is not None: g["individual"].append(ind)
        if val(x,"strategic") is not None: g["strategic"].append(val(x,"strategic"))
        if val(x,"pe") is not None and val(x,"other") is not None: g["financial"].append(val(x,"pe")+val(x,"other"))
        parts=[ind if ind is not None else 0, val(x,"strategic") or 0, val(x,"pe") or 0, val(x,"other") or 0]
        # completeness check only on rows without chart-mapped values
        if not x["cm"] and ind is not None or (not x["cm"] and sum(parts)>=95):
            s=sum(parts)
            if s>=95: comp.append([p/s*100 for p in parts[:2]]+[(parts[2]+parts[3])/s*100])
    d["pooled_strict"]={k:{"mean":round(st.mean(v),1) if v else None,"n":len(v)} for k,v in g.items()}
    d["pooled_complete_rows"]={"n":len(comp),**({k:round(st.mean(c[i] for c in comp),1) for i,k in enumerate(["individual","strategic","financial"])} if comp else {})}
    summ[b]=d
json.dump(summ,open("/tmp/claude-0/fit/ibba/summary.json","w"),indent=1)
print(len(rows))
