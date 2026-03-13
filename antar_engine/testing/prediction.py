import os, requests
from dotenv import load_dotenv
load_dotenv('.env')
from antar_engine import chart as C, vimsottari, transits, patra
from antar_engine import predictions
from main import build_predict_prompt, build_enrichment_context_v2, detect_concern, patra_to_context_block

cd = C.calculate_chart(birth_date='1970-11-02', birth_time='06:02', lat=18.1, lng=78.85, tz_offset=5.5, ayanamsa='lahiri')
jd = cd['birth_jd']
raw = vimsottari.calculate_vimsottari_from_chart(cd, jd)
vim = []
for p in raw.get('mahadashas',[]): vim.append({'lord_or_sign':p.get('lord',''),'start':p.get('start_date','')[:10],'end':p.get('end_date','')[:10],'duration_years':p.get('duration_years',0),'level':'mahadasha'})
for p in raw.get('antardashas',[]): vim.append({'lord_or_sign':p.get('lord',''),'start':p.get('start_date','')[:10],'end':p.get('end_date','')[:10],'duration_years':p.get('duration_years',0),'level':'antardasha'})
dashas = {'vimsottari': vim, 'jaimini': [], 'ashtottari': []}
tr_list = transits.calculate_transits(cd)
tr = {t['planet']: t for t in tr_list}

q = 'What is happening in my life right now and what should I focus on in the coming months?'
concern = detect_concern(q)

user_profile = {'marital_status':'married','children_status':'has_children',
    'career_stage':'senior','health_status':'good','financial_status':'stable','birth_country':'India'}
patra_obj = patra.build_patra_context('1970-11-02', user_profile, concern)
patra_ctx = patra_to_context_block(patra_obj)

pred = predictions.build_layered_predictions(
    user_id=None, chart_data=cd, dashas=dashas,
    current_transits=tr_list, life_events=[], supabase=None, concern=concern
)
pred_ctx = predictions.predictions_to_context_block(pred)
enrich = build_enrichment_context_v2(cd, dashas, tr)

prompt = build_predict_prompt(chart_data=cd, dashas=dashas, transits=tr, concern=concern, user_question=q, patra_context=patra_ctx)
prompt += f'\n\n{pred_ctx}\n\n{enrich}'
print('Prompt:', len(prompt), 'chars')
print('Sending to DeepSeek...')
key = os.environ.get('DEEPSEEK_API_KEY','')
r = requests.post('https://api.deepseek.com/v1/chat/completions',
    headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
    json={'model':'deepseek-chat','max_tokens':1200,'messages':[{'role':'user','content':prompt}]}, timeout=60)
print(r.json()['choices'][0]['message']['content'])

