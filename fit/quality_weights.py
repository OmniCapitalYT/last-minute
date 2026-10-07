"""Quality weights for owner dependence and management depth, from broker listings.

1. Huber regression of ln(ask / cash flow) on ln(cash flow), a hinge, industry and
   description phrases (hed.pkl from hedonic.py); standard errors from a bootstrap that
   resamples brokers.
2. Threshold model: a phrase marks the top share p of the latent dimension, so the gap in
   mean z between flagged and unflagged listings is phi(c)/(p(1-p)), c = Phi^-1(1-p).
   Effect per sd = |coefficient| / gap.
3. Relative weight = effect per sd / 0.0791, the per-sd effect each dimension has under
   equal weights at the median (phi(0) * mean(2 ln hi, 2 ln 1/lo) / 3).
4. Shrunk toward the equal weight with a N(1, 0.5^2) prior. Only the owner-operated phrase
   is used for owner dependence: "absentee / manager-run" disagrees with it (z = 2.3), and
   listing copy uses it loosely. Phrase flags are noisy, so both effects are
   attenuated, and the weights are lower bounds before shrinkage.
"""
import pandas as pd, numpy as np, json
from math import erf, sqrt, exp, log, pi
d=pd.read_pickle('/tmp/claude-0/fit/hed.pkl'); d=d[d.has_desc==1].copy()
feats=['absentee','owner_op','recurring','growth','repeat','books','staff_in','realestate','sba','franchise','relocatable']
d['hinge']=np.maximum(0,d.lcf-np.log(3e5))
inds=sorted(d.ind.unique()); D=pd.get_dummies(d.ind)[[i for i in inds if i!='other']].astype(float)
X=np.column_stack([d[['lcf','hinge']+feats].values,D.values]); y=d.ly.values
cl=pd.factorize(d.broker.fillna('na'))[0]
def huber(X,y,c=1.345,it=40):
    X=np.column_stack([np.ones(len(X)),X]); b=np.linalg.lstsq(X,y,rcond=None)[0]
    for _ in range(it):
        e=y-X@b; s=np.median(np.abs(e))/0.6745; u=np.abs(e)/(c*s); w=np.where(u<=1,1,1/u); W=np.sqrt(w)
        b=np.linalg.lstsq(X*W[:,None],y*W,rcond=None)[0]
    return b
b=huber(X,y); rng=np.random.default_rng(1); ub=np.unique(cl); B=[]
for r in range(150):
    pick=rng.choice(ub,len(ub)); idx=np.concatenate([np.where(cl==g)[0] for g in pick]); B.append(huber(X[idx],y[idx],it=25))
se=np.array(B).std(0)
coef={f:(float(b[3+i]),float(se[3+i])) for i,f in enumerate(feats)}
def Pinv(p):
    lo,hi=-10,10
    for _ in range(100):
        m=(lo+hi)/2
        if 0.5*(1+erf(m/sqrt(2)))<p: lo=m
        else: hi=m
    return m
beq=(log(1.3181)+log(1/0.7273))*0.3989423/3
def rel(f):
    p=d[f].mean(); c=Pinv(1-p); gap=exp(-c*c/2)/sqrt(2*pi)/(p*(1-p))
    return abs(coef[f][0])/gap/beq, coef[f][1]/gap/beq, p
def shrink(m,s,prior=1.0,ps=0.5):
    w0,w1=1/ps**2,1/s**2; return (w0*prior+w1*m)/(w0+w1), (w0+w1)**-.5
out={}
for k,f in [('own','owner_op'),('mgt','staff_in')]:
    m,s,p=rel(f); sm,ss=shrink(m,s)
    out[k]={'phrase':f,'share_flagged':round(p,4),'raw':round(m,3),'raw_se':round(s,3),'weight':round(sm,2),'se':round(ss,2)}
out['coefficients']={f:[round(v[0],3),round(v[1],3)] for f,v in coef.items()}
out['n']=int(len(d)); out['prior']='N(1, 0.5^2) on the relative weight'; out['beq']=round(beq,4)
print(json.dumps(out,indent=1)); json.dump(out,open('/tmp/claude-0/fit/quality_weights.json','w'))
