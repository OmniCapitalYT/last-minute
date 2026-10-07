import openpyxl, json, math
ws=openpyxl.load_workbook('/tmp/claude-0/bundle/data/us_6digitnaics_rcptsize_2022.xlsx',read_only=True).worksheets[0]
rows={}
for r in ws.iter_rows(min_row=4,values_only=True):
    if not r[3]: continue
    try: rows.setdefault(str(r[0]),{})[str(r[2])]=(float(r[3]),float(r[5]),float(r[7])*1000,float(r[9])*1000)
    except: pass
N6={"home":"238220","medical":"621111","vet":"541940","msp":"541511","prof":"541211","mfg":"339950","dist":"423310","staff":"561320","land":"561730","wash":"811192","auto":"811111","constr":"238990","fit":"713940","rest":"722511","ecom":"454110","saas":"511210"}
susb={}
for ind,c in N6.items():
    sz=rows[c]; tot=sz['01: Total']; kn=[]
    for k,(f,e,p,rc) in sorted(sz.items()):
        if k.startswith('01') or e<20 or f<20: continue
        kn.append([round(math.log(rc/f),4), round(rc/e), round(p/e)])
    susb[ind]={'naics':c,'knots':kn,'rpe':round(tot[3]/tot[1]),'ppe':round(tot[2]/tot[1])}
oews=json.load(open('oews.json'))
gm={k:{'naics':v['naics'],'p10':v['p10'],'p25':v['p25'],'p50':v['p50'],'p75':v['p75'] if v['p75']==v['p75'] else 208000.0,'p90':v['p90'] if v['p90']==v['p90'] else 208000.0} for k,v in oews.items()}
mg=json.load(open('margin.json')); sr=json.load(open('sba_rate.json'))
out={
 'model':'omni_fitted_v4','asof':'2026-10-07',
 'sba_rate':{'prime':6.75,'prime_asof':'2025-12-11','spread_knots':[[math.log(1e5),2.0],[math.log(7.5e5),2.0],[math.log(1.5e6),1.75],[math.log(3.5e6),1.5]],
   'n':sr['n_fy23'],'median_spread':sr['median_fy23'],'source':'SBA FOIA 7(a), change-of-ownership loans approved FY2023 (Oct 2022 - Sep 2023), initial rate minus WSJ prime on the approval date'},
 'jobs':{'by_industry':susb,'source':'Census SUSB 2022, US 6-digit NAICS by enterprise receipts size: receipts and payroll per paid employee'},
 'gm_wage':{'by_industry':gm,'wage_growth_2021_2026':1.218,'topcode':208000,'source':'BLS OEWS May 2021, SOC 11-1021 General and Operations Managers, by industry; scaled to 2026 by the ECI private wages and salaries index (5.7%, 4.6%, 4.1%, 3.5%, 3.5% assumed for 2026)'},
 'sde_margin':{'slope':round(mg['slope'],4),'ref_sde':2e5,'sd':round(mg['sd'],4),'ln_at_ref':{k:round(v,4) for k,v in mg['a'].items()},'n':mg['n'],'sde_range':[math.log(4e4),math.log(3e6)],
   'source':'DealLedger broker-direct listings (CC0), Feb-Oct 2026: robust regression of ln(cash flow / revenue) on ln(cash flow) with industry effects, n=5,055'},
 'quality_weights':{'own':0.90,'mgt':0.48,'se':{'own':0.32,'mgt':0.27},
   'hedonic':{'n':5714,'owner_operated':[-0.206,0.055],'absentee_or_manager_run':[0.021,0.058],'staff_in_place':[0.076,0.043],'recurring':[0.026,0.055],'growth':[0.044,0.036],'clean_books':[-0.023,0.108],'repeat_customers':[-0.116,0.044]},
   'source':'DealLedger listings with descriptions: Huber regression of ln(ask / cash flow) on ln(cash flow), industry and description phrases; broker-clustered bootstrap SEs. Per-sd effects from the threshold model, relative to the equal weight 0.079 per sd.'}
}
json.dump(out,open('fitted_v4.json','w'),separators=(',',':'))
print(len(json.dumps(out))); print(json.dumps(out['jobs']['by_industry']['home'])[:300])
