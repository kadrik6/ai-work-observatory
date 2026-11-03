"""Lisaallikate logist lehe andmed (a_lisa) ja Riigikogu kuud ning olekumärkus a_jaotused-sse."""
import json,re,sys
t=json.loads(open(sys.argv[1]).read())['logs_content']
e={}
for row in t.split('\n'):
    m=re.search(r'Z LISA (\S+) (.*)$',row)
    if m: e[m.group(1)]=json.loads(m.group(2))
e.pop('meta',None)
read=[]
for n in ('hacker_news','maailmapank','nber','riigikogu'):
    for k in (e.get(n) or {}).get('kirjed',[]):
        r={x:k.get(x) for x in ('allikas','liik','pealkiri','url','avaldatud','teemas','punkte','kommentaare','koneleja')}
        if r['pealkiri'] and ' -- by ' in r['pealkiri']: r['pealkiri']=r['pealkiri'].split(' -- by ')[0]
        if r['pealkiri']: r['pealkiri']=' '.join(re.sub(r'<[^>]+>',' ',r['pealkiri']).replace('&nbsp;',' ').split())
        if n=='nber': r['teemas']=bool(re.search(r'\b(AI|automation|artificial intelligence|generative|robot|machine learning|LLM)',r['pealkiri'] or '',re.I))
        read.append(r)
json.dump(read,open('a_lisa.json','w'),ensure_ascii=False,indent=1)
j=json.load(open('a_jaotused.json'))
j=[r for r in j if r['jaotus']!='rk_kuu' and not (r['jaotus']=='kokku' and r['nimi']=='lisa_markus')]
for r in (e.get('riigikogu') or {}).get('aegrida') or []:
    j.append({'jaotus':'rk_kuu','nimi':r['kuu'],'arv':r['sonavotte'],'liik':''})
NIMI={'gdelt_maailm':'GDELT','gdelt_eesti':'GDELT','vikipeedia':'Vikipeedia','semantic_scholar':'Semantic Scholar'}
ei=sorted({NIMI.get(n,n) for n,v in e.items() if not v['kirjed'] and not v.get('aegrida')})
j.append({'jaotus':'kokku','nimi':'lisa_markus','arv':None,'liik':('GitHubist ei saa praegu lugeda: '+', '.join(ei)+'.') if ei else ''})
json.dump(j,open('a_jaotused.json','w'),ensure_ascii=False,indent=1)
from collections import Counter
print(Counter((r['allikas'],r['teemas']) for r in read)); print([x for x in j if x['jaotus']=='rk_kuu']); print(ei)
for n,v in e.items(): print(n, len(v['kirjed']), [x[-70:] for x in v['vead'][:2]])
