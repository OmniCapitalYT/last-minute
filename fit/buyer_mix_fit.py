"""Multinomial logit of IBBA buyer-group shares (individual / strategic / financial) on
ln(deal value), weighted by the number of complete band-quarters. Reads summary.json
written by ibba_buyer_mix.py; writes buyer_mix_fit.json (MODELS.fitted.buyer_mix)."""
import json, math, numpy as np
d=json.load(open('ibba/summary.json'))
bands=[('<500K',2.5e5),('500K-1M',math.sqrt(5e5*1e6)),('1M-2M',math.sqrt(2e12)),('2M-5M',math.sqrt(1e13)),('5M-50M',math.sqrt(2.5e14))]
X=[];Y1=[];Y2=[];W=[]
for b,c in bands:
    p=d[b]['pooled_complete_rows']; s=np.array([p['individual'],p['strategic'],p['financial']])/100
    s=np.maximum(s,.01); s/=s.sum()
    X.append(math.log(c/1e6)); Y1.append(math.log(s[1]/s[0])); Y2.append(math.log(s[2]/s[0])); W.append(p['n'])
X=np.array(X); W=np.sqrt(np.array(W,float)); A=np.column_stack([np.ones(len(X)),X])
b1=np.linalg.lstsq(A*W[:,None],np.array(Y1)*W,rcond=None)[0]; b2=np.linalg.lstsq(A*W[:,None],np.array(Y2)*W,rcond=None)[0]
json.dump({'strategic':list(b1),'financial':list(b2),'x0':1e6},open('buyer_mix_fit.json','w'))
print('strategic/individual',b1,'financial/individual',b2)
