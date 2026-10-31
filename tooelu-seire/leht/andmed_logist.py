"""Analüüsi käivituse logist lehe andmed (a_aastad, a_teemad, a_tood, a_jaotused)."""
import json,re,sys,unicodedata
LOG,RUN=sys.argv[1],sys.argv[2]
t=json.loads(open(LOG).read())['logs_content']
o={}
for row in t.split('\n'):
    m=re.search(r'Z ANALYYS (\S+) (.*)$',row)
    if m: o[m.group(1)]=json.loads(m.group(2))
vana=json.load(open(sys.argv[3] if len(sys.argv)>3 else 'osad.json'))
for k in vana:
    if k not in o: print('vanast käivitusest:',k); o[k]=vana[k]
json.dump(o,open('osad3.json','w'),ensure_ascii=False,indent=1)
def n(t): return re.sub(r'[^a-z0-9]+',' ',unicodedata.normalize('NFKD',t).encode('ascii','ignore').decode().lower()).strip()
T={'kadu':'Töökohtade kadu','varbamine':'Värbamine ja vabad töökohad','umberkorraldus':'Töö ja organisatsiooni ümberkorraldus','majandus':'Majanduslik mõju','tootajad':'Töötajate olukord','genai':'Generatiivne tehisaru'}
yr={int(r['voti']):r['arv'] for r in o['aastad']}
aastad=[]
for y in sorted(yr):
    row={'aasta':y,'koik':yr[y],'poolik':y==2026}
    for k in T: row[k]={int(r['voti']):r['arv'] for r in o['teema_'+k]}.get(y)
    aastad.append(row)
teemad=[]
for k,nm in T.items():
    d={int(r['voti']):r['arv'] for r in o['teema_'+k]}
    teemad.append({'voti':k,'nimi':nm,'a2025':d[2025],'a2026':d[2026],'kasv':round(d[2026]/d[2025],2),'osa2025':round(100*d[2025]/yr[2025],1),'osa2026':round(100*d[2026]/yr[2026],1)})
teemad.sort(key=lambda r:-r['kasv'])
tuumid={w['voti'] for w in o['enim_tsiteeritud_tuum']}
def klass(w):
    if w['liik']=='dissertation': return 'lõputöö'
    if w['kanali_liik']=='repository': return 'eeltrükk või töödokument'
    if w.get('tuum') is True or w['voti'] in tuumid: return 'tuumajakiri'
    if w['kanali_liik']=='journal': return 'muu ajakiri' if w.get('tuum') is False else 'ajakiri'
    if w['liik'] in ('book','book-chapter') or w['kanali_liik'] in ('book series','ebook platform'): return 'raamat'
    return 'muu'
AI=re.compile(r'\b(ai|a\.i\.|artificial intelligence|generative|chatgpt|llms?|large language|automation|automati|robot|machine learning|algorithm|digital|tehisintellekt|tehisaru|keelemudel|masinõpe|automatiseer|digi)',re.I)
def rida(grupp,w,moodus=None):
    return {'id':grupp+'-'+w['voti'],'grupp':grupp,'pealkiri':w['pealkiri'].strip('* '),'avaldatud':w['avaldatud'],'viiteid':w['viiteid'],
            'kanal':(w['kanal'] or '').replace(' (CERN European Organization for Nuclear Research)','').replace(' (Cornell University)',''),
            'klass':klass(w),'url':w['url'],'teine':'','moodus':moodus}
tood=[]
for grupp,lst in [('koik',o['enim_tsiteeritud']),('aasta',o['enim_tsiteeritud_aasta']),('uusimad',o['uusimad'])]:
    seen={}
    for w in lst:
        key=n(w['pealkiri'])
        if key in seen:
            seen[key]['teine']=f"{w['kanal']}: {w['viiteid']} viidet"; continue
        r=rida(grupp,w); seen[key]=r; tood.append(r)
seen={}; valja=0
for moodus,lst in [('autor',o['eesti_autorid_uusimad']+o['eesti_autorid_tsiteeritud']),('mainitud',o['eesti_mainitud_uusimad']),('keel',o['eesti_keeles'])]:
    for w in lst:
        key=n(w['pealkiri'])
        if key in seen: continue
        seen[key]=1
        if not AI.search(w['pealkiri']): valja+=1; continue
        tood.append(rida('eesti',w,moodus))
j=[]
for r in o['riigid'][:12]: j.append({'jaotus':'riik','nimi':r['nimi'],'arv':r['arv'],'liik':''})
for r in o['asutused'][:10]: j.append({'jaotus':'asutus','nimi':r['nimi'],'arv':r['arv'],'liik':''})
repo={'SSRN Electronic Journal','Zenodo (CERN European Organization for Nuclear Research)','arXiv (Cornell University)','Research Square','Figshare','OSF Preprints (OSF Preprints)','Preprints.org','RePEc: Research Papers in Economics','DergiPark (Istanbul University)'}
for r in o['kanalid'][:12]:
    nm=r['nimi'].replace(' (CERN European Organization for Nuclear Research)','').replace(' (Cornell University)','').replace(' (OSF Preprints)','').replace(' (Istanbul University)','')
    if nm.isupper(): nm=nm.title()
    j.append({'jaotus':'kanal','nimi':nm,'arv':r['arv'],'liik':'hoidla' if r['nimi'] in repo else 'ajakiri'})
kl={r['voti']:r['arv'] for r in o['kanali_liigid']}
tu={r['voti']:r['arv'] for r in o['tuumkanal']}
muu=sum(v for k,v in kl.items() if k not in('journal','repository','conference'))
j+= [{'jaotus':'usaldus','nimi':'Tuumajakiri','arv':tu['true'],'liik':'tuum'},
     {'jaotus':'usaldus','nimi':'Muu ajakiri','arv':kl['journal']+kl.get('conference',0)-tu['true'],'liik':'ajakiri'},
     {'jaotus':'usaldus','nimi':'Eeltrükiserver või hoidla','arv':kl['repository'],'liik':'hoidla'},
     {'jaotus':'usaldus','nimi':'Muu','arv':muu,'liik':'muu'}]
for r in o['eesti_autorid_aastad']: j.append({'jaotus':'eesti_aasta','nimi':r['voti'],'arv':r['arv'],'liik':''})
for r in o['eesti_autorid_asutused'][:8]: j.append({'jaotus':'eesti_asutus','nimi':r['nimi'],'arv':r['arv'],'liik':''})
S=lambda k: sum(r['arv'] for r in o[k])
ea,em,ek=S('eesti_autorid_aastad'),S('eesti_mainitud_aastad'),S('eesti_keeles_aastad')
j+= [{'jaotus':'eesti_moodus','nimi':'Eesti autor','arv':ea,'liik':''},{'jaotus':'eesti_moodus','nimi':'Eesti mainitud','arv':em,'liik':''},{'jaotus':'eesti_moodus','nimi':'Eesti keeles','arv':ek,'liik':''}]
av={r['voti']:r['arv'] for r in o['avatud']}
kokku={'aeg':o['meta']['aeg'],'t2025':yr[2025],'t2026':yr[2026],'alates2023':sum(r['arv'] for r in o['liigid']),
 'vanad':o['vanad_koik'],'viiteta':o['vanad_viiteta'],'tagasi':o['tagasi_voetud'],'avatud':av['true'],'suletud':av['false'],
 'tuum':tu['true'],'kanaliga':tu['true']+tu['false'],'eesti':ea,'eesti_autorid':ea,'eesti_mainitud':em,'eesti_keeles':ek,'eesti_valja':valja,
 'lai2026':{r['voti']:r['arv'] for r in o['lai_aastad']}['2026'],'lai2025':{r['voti']:r['arv'] for r in o['lai_aastad']}['2025'],'eesti2026':{r['voti']:r['arv'] for r in o['eesti_autorid_aastad']}.get('2026',0),
 'kaivitus':f'https://github.com/kadrik6/ai-work-observatory/actions/runs/{RUN}'}
for k,v in kokku.items(): j.append({'jaotus':'kokku','nimi':k,'arv':v if isinstance(v,(int,float)) else None,'liik':v if isinstance(v,str) else ''})
for nm,d in [('a_aastad',aastad),('a_teemad',teemad),('a_tood',tood),('a_jaotused',j)]:
    json.dump(d,open(nm+'.json','w'),ensure_ascii=False,indent=1)
from collections import Counter
print('tood',Counter(t['grupp'] for t in tood),'valja',valja)
print('klassid',Counter((t['grupp'],t['klass']) for t in tood))
print('kokku',{k:v for k,v in kokku.items() if k!='kaivitus'})
for t in tood:
    if 'Quarterly' in (t['kanal'] or ''): print('QJE',t['klass'])
