import openpyxl, json, math
ws=openpyxl.load_workbook('/tmp/claude-0/bundle/data/us_6digitnaics_rcptsize_2022.xlsx',read_only=True).worksheets[0]
rows={}
for r in ws.iter_rows(min_row=4,values_only=True):
    if not r[3]: continue
    try: rows.setdefault(str(r[0]),{})[str(r[2])]=(float(r[3]),float(r[5]),float(r[7])*1000,float(r[9])*1000)
    except: pass
# 4-digit industry groups (sector for manufacturing and wholesale): the 6-digit codes the
# value model uses are single niches (lumber wholesale, sign makers), too narrow for
# staffing ratios
N6={"home":"2382","medical":"6211","vet":"5419","msp":"5415","prof":"5412","mfg":"31-33","dist":"42","staff":"5613","land":"5617","wash":"8111","auto":"8111","constr":"2389","fit":"7139","rest":"7225","ecom":"4541","saas":"5112"}
susb={}
for ind,c in N6.items():
    sz=rows[c]; tot=sz['01: Total']; kn=[]; cum=0
    for k,(f,e,p,rc) in sorted(sz.items()):
        if k.startswith('01') or e<20 or f<20: continue
        # [ln receipts per firm, receipts per employee, payroll per employee,
        #  employment-weighted share of the industry in smaller firms (band midpoint)]
        kn.append([round(math.log(rc/f),4), round(rc/e), round(p/e), round((cum+e/2)/tot[1],4)]); cum+=e
    susb[ind]={'naics':c,'knots':kn,'rpe':round(tot[3]/tot[1]),'ppe':round(tot[2]/tot[1])}
# GM wages: OEWS May 2025, EB-shrunk, x ECI to 2026Q2; written by `python3 -I oews_refresh.py --write-repo`
# (oews.py and its May-2021 oews.json are superseded)
mg=json.load(open('margin.json')); QWJ=json.load(open('quality_weights.json'))
BM=json.load(open('ibba/summary.json'))
out={
 'model':'omni_fitted_v4','asof':'2026-10-07',
 # SBA rate: Fed H.15 prime (7.00% since 2026-09-17) + median spread of FY2025-26 variable-rate change-of-ownership
 # 7(a) loans over the prime on the first business day of the approval month (13 CFR 120.214(c)); written by
 # fit/sba_risk_refresh.py (its MODELS_fitted_sba_rate.json, copied here). sba_rate.py and its FY2023 table are superseded.
 'sba_rate':json.load(open('sba_rate_fy2025_26.json')),
 'jobs':{'by_industry':susb,'source':'Census SUSB 2022, US 6-digit NAICS by enterprise receipts size: receipts and payroll per paid employee'},
 'gm_wage':json.load(open('gm_wage.json')),
 'sde_margin':{'slope':round(mg['slope'],4),'ref_sde':2e5,'sd':round(mg['sd'],4),'ln_at_ref':{k:round(v,4) for k,v in mg['a'].items()},'n':mg['n'],'sde_range':[math.log(4e4),math.log(3e6)],
   'source':'DealLedger broker-direct listings (CC0), Feb-Oct 2026: robust regression of ln(cash flow / revenue) on ln(cash flow) with industry effects, n=5,055'},
 'quality_weights':{'own':QWJ['own']['weight'],'mgt':QWJ['mgt']['weight'],'se':{'own':QWJ['own']['se'],'mgt':QWJ['mgt']['se']},'raw':{'own':[QWJ['own']['raw'],QWJ['own']['raw_se']],'mgt':[QWJ['mgt']['raw'],QWJ['mgt']['raw_se']]},
   'hedonic':dict(n=QWJ['n'],owner_operated=QWJ['coefficients']['owner_op'],absentee_or_manager_run=QWJ['coefficients']['absentee'],staff_in_place=QWJ['coefficients']['staff_in'],recurring=QWJ['coefficients']['recurring'],growth=QWJ['coefficients']['growth'],clean_books=QWJ['coefficients']['books'],repeat_customers=QWJ['coefficients']['repeat']),'prior':QWJ['prior'],
   'source':'DealLedger listings with descriptions: Huber regression of ln(ask / cash flow) on ln(cash flow), industry and description phrases; broker-clustered bootstrap SEs. Per-sd effects from the threshold model, relative to the equal weight 0.079 per sd.'}
}
# buyer-type mix: pooled complete band-quarters, interpolated in ln(value) between band
# centres as log-ratios to individuals (flat beyond), the way the other IBBA bands are read
bands=[('<500K',2.5e5),('500K-1M',math.sqrt(5e5*1e6)),('1M-2M',math.sqrt(2e12)),('2M-5M',math.sqrt(1e13)),('5M-50M',math.sqrt(2.5e14))]
kn=[];ns=[]
for b,c in bands:
    q=BM[b]['pooled_complete_rows']; s=[max(q['individual'],1)/100,max(q['strategic'],1)/100,max(q['financial'],1)/100]
    kn.append([round(math.log(c),4),round(math.log(s[1]/s[0]),4),round(math.log(s[2]/s[0]),4)]); ns.append(q['n'])
out['buyer_mix']={'knots':kn,'n_complete':ns,'n_rows':154,'periods':41,
  'source':'IBBA / M&A Source Market Pulse 2012-2023: buyer-type shares by deal-size band from the band-quarters whose stated shares cover at least 95% (individual = first-time + serial; financial = PE + other), interpolated in ln(deal value) between band centres'}
json.dump(out,open('fitted_v4.json','w'),separators=(',',':'))
print(len(json.dumps(out))); print(json.dumps(out['jobs']['by_industry']['home'])[:300])
