import pandas as pd, numpy as np, json
d=pd.read_pickle('hed.pkl')
d=d[d.has_desc==1].copy()
d['lrev']=np.log(d.rev.where(d.rev>d.cf*1.0))
feats=['absentee','owner_op','recurring','growth','repeat','books','staff_in','realestate','sba','franchise','relocatable']
def ols(X,y,cl=None):
    X=np.column_stack([np.ones(len(X)),X]); b=np.linalg.lstsq(X,y,rcond=None)[0]; e=y-X@b
    XtXi=np.linalg.inv(X.T@X)
    if cl is None: S=(X*e[:,None]).T@(X*e[:,None])
    else:
        S=0
        for g in np.unique(cl):
            m=cl==g; s=(X[m]*e[m,None]).sum(0); S=S+np.outer(s,s)
    V=XtXi@S@XtXi*len(y)/(len(y)-X.shape[1]); r2=1-e.var()/y.var()
    return b,np.sqrt(np.diag(V)),r2,e
inds=sorted(d.ind.unique()); D=pd.get_dummies(d.ind)[ [i for i in inds if i!='other'] ].astype(float)
d['hinge']=np.maximum(0,d.lcf-np.log(3e5))
base=['lcf','hinge']
cl=pd.factorize(d.broker.fillna('na'))[0]
for spec,cols in [('size+ind',base),('size+ind+feat',base+feats)]:
    X=np.column_stack([d[cols].values,D.values]); b,se,r2,e=ols(X,d.ly.values,cl)
    print('==',spec,'n',len(d),'R2',round(r2,3))
    names=['const']+cols+list(D.columns)
    for n_,bb,s in zip(names,b,se):
        if n_ in feats or n_ in base: print(f'  {n_:12s} {bb:+.3f}  se {s:.3f}  t {bb/s:+.1f}')
# with margin where revenue known
m=d.lrev.notna()
dd=d[m]; X=np.column_stack([dd[base+feats].values,np.log(dd.cf/dd.rev).values,D[m].values]); b,se,r2,e=ols(X,dd.ly.values,cl[m.values])
print('== with log margin n',len(dd),'R2',round(r2,3)); names=['const']+base+feats+['lmargin']
for n_,bb,s in zip(names,b,se): print(f'  {n_:12s} {bb:+.3f}  se {s:.3f}  t {bb/s:+.1f}')

def huber(X,y,c=1.345,it=50):
    X=np.column_stack([np.ones(len(X)),X]); b=np.linalg.lstsq(X,y,rcond=None)[0]
    for _ in range(it):
        e=y-X@b; s=np.median(np.abs(e))/0.6745; u=np.abs(e)/(c*s); w=np.where(u<=1,1,1/u)
        W=np.sqrt(w); b=np.linalg.lstsq(X*W[:,None],y*W,rcond=None)[0]
    return b
print('== Huber, size+ind+feat')
X=np.column_stack([d[base+feats].values,D.values]); b=huber(X,d.ly.values)
# bootstrap by broker for SE
rng=np.random.default_rng(1); B=[]
ub=np.unique(cl)
for r in range(150):
    pick=rng.choice(ub,len(ub)); idx=np.concatenate([np.where(cl==g)[0] for g in pick])
    B.append(huber(X[idx],d.ly.values[idx],it=25))
B=np.array(B); se=B.std(0)
for n_,bb,s in zip(['const']+base+feats,b,se): print(f'  {n_:12s} {bb:+.3f}  se {s:.3f}  t {bb/s:+.1f}')
