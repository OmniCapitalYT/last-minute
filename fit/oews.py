import pyreadr, json, sys, pandas as pd
r=pyreadr.read_r('/tmp/claude-0/dl/oews2021_cran/data/oews2021.rda'); df=list(r.values())[0]
g=df[df.OCC_CODE=='11-1021'].copy()
print(g.columns.tolist()); print(g.I_GROUP.value_counts())
N6=json.loads(sys.argv[1]); N6['saas']='511200'; N6['ecom']='454100'
def num(x):
    try: return float(str(x).replace(',',''))
    except: return None
out={}
for ind,code in N6.items():
    hit=None
    for k in (6,5,4,3,2):
        c=code[:k]
        m=g[g.NAICS.astype(str).str.startswith(c) & (g.NAICS.astype(str).str.rstrip('0').str.len()<=k+0)]
        m=g[g.NAICS.astype(str)==c.ljust(6,'0')]
        if len(m): hit=m.iloc[0]; break
    if hit is None: hit=g[g.NAICS.astype(str)=='000000'].iloc[0]
    out[ind]={'naics':str(hit.NAICS),'title':str(hit.NAICS_TITLE),'p10':num(hit.A_PCT10),'p25':num(hit.A_PCT25),'p50':num(hit.A_MEDIAN),'p75':num(hit.A_PCT75),'p90':num(hit.A_PCT90),'emp':num(hit.TOT_EMP)}
    print(ind,out[ind])
json.dump(out,open('oews.json','w'))
