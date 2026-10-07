import pandas as pd, numpy as np, json
d=pd.read_pickle('hed.pkl')
m=d[(d.rev>d.cf)&(d.rev>0)].copy(); m['lm']=np.log(m.cf/m.rev); m=m[(m.cf/m.rev>=.02)&(m.cf/m.rev<=.9)]
m['lcf']=np.log(m.cf)
print('n',len(m)); print(m.groupby('ind').apply(lambda g:pd.Series({'n':len(g),'med_margin':np.exp(g.lm.median()),'med_cf':g.cf.median()})).round(3))
inds=sorted(m.ind.unique()); D=pd.get_dummies(m.ind)[inds].astype(float).values
X=np.column_stack([m.lcf.values-np.log(2e5),D]); 
# Huber
def huber(X,y,c=1.345,it=60):
    b=np.linalg.lstsq(X,y,rcond=None)[0]
    for _ in range(it):
        e=y-X@b; s=np.median(np.abs(e))/0.6745; u=np.abs(e)/(c*s); w=np.where(u<=1,1,1/u); W=np.sqrt(w)
        b=np.linalg.lstsq(X*W[:,None],y*W,rcond=None)[0]
    return b,e
b,e=huber(X,m.lm.values)
slope=b[0]; a=dict(zip(inds,b[1:]))
# empirical-Bayes shrinkage toward the pooled level: an industry with n listings keeps
# n/(n+50) of its own deviation (vet has 15 listings, staffing 48)
cnt={k:int((m.ind==k).sum()) for k in inds}; abar=sum(a[k]*cnt[k] for k in inds)/sum(cnt.values())
a={k:(cnt[k]*a[k]+50*abar)/(cnt[k]+50) for k in inds}
sd=np.median(np.abs(e))/0.6745
print('slope on ln(SDE) %.3f'%slope,'robust sd %.3f'%sd)
for k in inds: print(k,'margin at $200k SDE %.3f'%np.exp(a[k]),'at $1M %.3f'%np.exp(a[k]+slope*np.log(5)))
json.dump({'slope':slope,'ref_sde':2e5,'sd':sd,'a':a,'n':{k:int((m.ind==k).sum()) for k in inds}},open('margin.json','w'))
