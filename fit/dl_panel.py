import pandas as pd, glob, numpy as np, re
base='/tmp/claude-0/dl/jeffsosville_dealledger/data/'
snaps=sorted(glob.glob(base+'snapshots/*/listings.csv'))
frames=[]
for f in snaps:
    d=pd.read_csv(f,low_memory=False); d['snap']=f.split('/')[-2]; frames.append(d)
A=pd.concat(frames,ignore_index=True)
print(A.shape, A.columns.tolist())
A['key']=A['url'].fillna(A['source_url']); key='key'
A['desc']=A['description'].fillna(A['raw_text'])
for c in ['asking_price','cash_flow','revenue']: A[c]=pd.to_numeric(A[c],errors='coerce')
A['snap']=pd.to_datetime(A['snap'])
g=A.sort_values('snap').groupby(key)
P=pd.DataFrame({
 'first':g['snap'].min(),'last':g['snap'].max(),'n':g['snap'].count(),
 'ask_first':g['asking_price'].first(),'ask_last':g['asking_price'].last(),
 'cf':g['cash_flow'].last(),'rev':g['revenue'].last(),
 'status_last':g['status'].last(),
 'title':g['title'].last(),
 'desc':g['desc'].last(),
 'vertical':g['vertical'].last(),'state':g['state'].last(),'broker':g['broker_name'].last(),'bt':g['business_type'].last()})
P['sold_any']=g['status'].apply(lambda s:(s.astype(str).str.lower()=='sold').any())
print(P.shape); print(P['status_last'].value_counts().head()); print(P['sold_any'].sum())
print('snap dates',A['snap'].min(),A['snap'].max(), A['snap'].nunique())
P.to_pickle('panel.pkl')
print(P[['ask_first','cf','rev']].notna().sum())
