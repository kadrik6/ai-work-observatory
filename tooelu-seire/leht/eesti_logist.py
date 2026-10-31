"""Eesti allikate logist lehe andmed (a_eesti_allikad) ja olekumärkus a_jaotused-sse."""
import json,re,sys
t=json.loads(open(sys.argv[1]).read())['logs_content']
e={}
for row in t.split('\n'):
    m=re.search(r'Z EESTI (\S+) (.*)$',row)
    if m: e[m.group(1)]=json.loads(m.group(2))
e.pop('meta',None)
read=[]
for n,v in e.items():
    for k in v['kirjed']:
        read.append({'allikas':n,'liik':k['liik'],'pealkiri':k['pealkiri'],'url':k['url'],'avaldatud':k['avaldatud'],'teemas':k['teemas']})
NIMI={'praxis':'Praxis','tu_dspace':'Tartu Ülikooli lõputööd','taltech_digikogu':'TalTechi digikogu','etis':'ETIS','arenguseire':'Arenguseire','oska':'OSKA','err':'ERR','novaator':'Novaator'}
ei=[NIMI.get(n,n) for n,v in e.items() if not any(k['teemas'] for k in v['kirjed'])]
markus=('Veel ei tööta: '+', '.join(ei)+'.') if ei else ''
json.dump(read,open('a_eesti_allikad.json','w'),ensure_ascii=False,indent=1)
j=json.load(open('a_jaotused.json'))
j=[r for r in j if not (r['jaotus']=='kokku' and r['nimi']=='ea_markus')]
j.append({'jaotus':'kokku','nimi':'ea_markus','arv':None,'liik':markus})
json.dump(j,open('a_jaotused.json','w'),ensure_ascii=False,indent=1)
from collections import Counter
print(Counter((r['allikas'],r['teemas']) for r in read)); print(markus)
