import pandas as pd, numpy as np, json
f='/tmp/claude-0/dl/sba_foia_csis/foia-7afy2020-present-asof-230930.csv'
d=pd.read_csv(f,usecols=['GrossApproval','ApprovalDate','InitialInterestRate','TermInMonths','NaicsCode','BusinessAge','JobsSupported','subpgmdesc','FranchiseCode'],low_memory=False,encoding='latin-1')
print(d.BusinessAge.value_counts())
a=d[d.BusinessAge.astype(str).str.contains('Change of Ownership',case=False)].copy()
a['date']=pd.to_datetime(a.ApprovalDate,format='%m/%d/%Y')
PR=[('2019-08-01',5.25),('2019-09-19',5.00),('2019-10-31',4.75),('2020-03-04',4.25),('2020-03-16',3.25),('2022-03-17',3.50),('2022-05-05',4.00),('2022-06-16',4.75),('2022-07-28',5.50),('2022-09-22',6.25),('2022-11-03',7.00),('2022-12-15',7.50),('2023-02-02',7.75),('2023-03-23',8.00),('2023-05-04',8.25),('2023-07-27',8.50)]
pr=pd.Series([p for _,p in PR],index=pd.to_datetime([d_ for d_,_ in PR]))
a['prime']=pr.reindex(a.date.sort_values().unique(),method='ffill').reindex(a.date).values
a['spread']=a.InitialInterestRate-a.prime
a=a[(a.spread>-1)&(a.spread<9)]
bins=[0,5e4,1.5e5,2.5e5,3.5e5,5e5,1e6,2e6,5e6+1]
a['band']=pd.cut(a.GrossApproval,bins)
print(a.groupby('band').spread.describe()[['count','25%','50%','75%']])
# recent regime only (FY2023: approval after 2022-10-01)
r=a[a.date>='2022-10-01']
t=r.groupby('band').spread.median(); print('FY23 medians'); print(t, len(r))
print('overall FY23 median',r.spread.median(),'n',len(r),'median loan',r.GrossApproval.median())
# continuous fit: spread on log loan size (FY23)
x=np.log(r.GrossApproval); X=np.column_stack([np.ones(len(x)),x]); b=np.linalg.lstsq(X,r.spread,rcond=None)[0]; print('spread = %.3f %+.3f ln(loan)'%tuple(b))
out={'by_band_fy23':{str(k):float(v) for k,v in t.items()},'n_fy23':int(len(r)),'median_fy23':float(r.spread.median()),'n_all':int(len(a))}
json.dump(out,open('sba_rate.json','w'))
# jobs per $ loan by naics2 for later (not used)
