import pandas as pd, numpy as np, re, json
P=pd.read_pickle('panel.pkl')
P['ask']=P['ask_last'].fillna(P['ask_first'])
d=P[(P.ask>=2e4)&(P.ask<=5e7)&(P.cf>=1e4)&(P.cf<=2e7)].copy()
d['mult']=d.ask/d.cf; d=d[(d.mult>=.3)&(d.mult<=15)]
d['text']=(d['title'].fillna('')+' . '+d['bt'].fillna('')+' . '+d['desc'].fillna('')).str.lower()
d=d.drop_duplicates(subset=['ask','cf','title'])
print('n',len(d),'with desc>200',(d.desc.fillna('').str.len()>200).sum(), 'with rev',d.rev.notna().sum())
IND={
 'rest':r'restaurant|pizza|cafe|coffee|bakery|bar\b|pub\b|tavern|grill|diner|sushi|taco|food truck|catering|brewery|ice cream|yogurt|deli\b|bistro',
 'home':r'hvac|plumb|electrical contractor|electrician|heating|air condition|roofing|pest control|garage door|handyman|home service|septic|water heater',
 'medical':r'dental|dentist|medical practice|clinic|physician|chiropract|physical therap|optometr|med ?spa|orthodont|pharmacy|home health|urgent care',
 'vet':r'veterinar|animal hospital|vet clinic|pet clinic',
 'msp':r'managed service|it services|it support|msp\b|cybersecurity|network services',
 'saas':r'saas|software|subscription platform|app\b',
 'prof':r'accounting|cpa\b|bookkeeping|tax practice|law firm|insurance agency|consulting firm|engineering firm|architect',
 'mfg':r'manufactur|machine shop|fabricat|cnc|plastics|printing company',
 'dist':r'distribut|wholesale',
 'ecom':r'e-?commerce|amazon|shopify|online store|fba\b',
 'staff':r'staffing|recruit|employment agency|temp agency',
 'land':r'landscap|lawn|tree service|irrigation|snow removal',
 'wash':r'car wash|carwash|laundromat|laundry|dry clean',
 'auto':r'auto repair|automotive|collision|body shop|tire|oil change|transmission|mechanic',
 'constr':r'construction|contractor|concrete|excavat|paving|drywall|framing|remodel',
 'fit':r'fitness|gym\b|yoga|pilates|martial arts|studio|crossfit|dance',
}
def cls(t):
    for k,p in IND.items():
        if re.search(p,t): return k
    return 'other'
d['ind']=d.text.apply(cls); print(d.ind.value_counts())
F={
 'absentee':r'absentee|semi-absentee|semi absentee|passive owner|owner not on site|manager run|management in place|manager in place|run by (a )?manager|turnkey operation|owner works? (only )?(a few|part)',
 'owner_op':r'owner[- ]operat|owner works full|owner is (the )?(key|primary)|owner performs|owner-run',
 'recurring':r'recurring|subscription|contract(s|ed)? (revenue|customers|clients)|maintenance (agreements|contracts)|service agreements|membership|retainer|route\b',
 'growth':r'growing|growth|year[- ]over[- ]year|record (year|sales|revenue)|increas(ing|ed) (sales|revenue)',
 'decline':r'declin|decreas|down from|lost (a )?(major|key)',
 'diversified':r'diversified customer|no (single )?customer (accounts|represents)|broad customer base|diverse client',
 'concentr':r'major customer|largest customer|one (customer|client) (accounts|represents)|key account',
 'repeat':r'repeat customers|loyal customer|long[- ]term (clients|customers)|established customer base|customer base of',
 'books':r'clean books|audited|reviewed financ|verified financ|tax returns|cpa[- ]prepared|accrual|quickbooks|p&l',
 'staff_in':r'trained staff|experienced staff|employees? (in place|will stay)|key employees|staff in place|team in place',
 'realestate':r'real estate (included|available)|property included|includes (the )?(building|real estate)',
 'sba':r'sba (pre-?qualified|approved|financing)|pre-?qualified',
 'franchise':r'franchise',
 'relocatable':r'relocatable|home[- ]based|work from home',
}
for k,p in F.items(): d[k]=d.text.str.contains(p,regex=True).astype(int)
d['lcf']=np.log(d.cf); d['ly']=np.log(d.mult)
d['has_desc']=(d.desc.fillna('').str.len()>200).astype(int)
d.to_pickle('hed.pkl')
print(d[list(F)].mean().round(3))
