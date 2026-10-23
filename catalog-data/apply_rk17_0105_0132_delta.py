"""Apply approved RK17-0105..0132 typed terms to the permanent concept registry."""
import json
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'source-cards' / 'RK17_0105_0132_approved.json'
REGISTRY = ROOT / 'concept_id_registry.json'
BATCH_ID = 'RK17-0105-0132'
FIELD_TYPES = {
    'primary_subjects':'SUBJECT', 'secondary_subjects':'SUBJECT', 'role':'ROLE',
    'mood':'MOOD', 'themes':'THEME', 'actions':'ACTION', 'objects':'OBJECT',
    'clothing':'CLOTHING', 'decorations':'DECORATION', 'style':'STYLE', 'intent':'INTENT',
}

def norm(value):
    return ' '.join(unicodedata.normalize('NFC', value).strip().upper().split())

def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8', newline='\n')

source = json.loads(SOURCE.read_text(encoding='utf-8'))
registry = json.loads(REGISTRY.read_text(encoding='utf-8'))
active = [x for x in registry['concepts'] if x['lifecycle'] == 'active']
by_binding = {(x['field'],x['source_normalized']):x['concept_id'] for x in registry['source_bindings']}
by_canonical = {}
for concept in active:
    by_canonical.setdefault(concept['canonical'],[]).append(concept)
created_now=[]; used=set(); bindings_added=[]
next_sequence=registry['allocation']['next_sequence']

def allocate(canonical, concept_type):
    global next_sequence
    concept_id=f'GSC-{next_sequence:06d}'; next_sequence+=1
    concept={'canonical':canonical,'concept_id':concept_id,'concept_type':concept_type,'lifecycle':'active',
             'sense_key':f'{BATCH_ID}_{concept_id}',
             'history':[{'batch_id':BATCH_ID,'event':'created_from_approved_semantic_card','id_preserved_on_future_rename_or_retype':True}]}
    registry['concepts'].append(concept); active.append(concept); by_canonical.setdefault(canonical,[]).append(concept); created_now.append(concept)
    return concept_id

for record in source['records']:
    for field,concept_type in FIELD_TYPES.items():
        value=record.get(field)
        terms=value if isinstance(value,list) else [value] if value else []
        for term in terms:
            normalized=norm(term); key=(field,normalized)
            if key in by_binding:
                used.add(by_binding[key]); continue
            matches=by_canonical.get(normalized,[])
            if len(matches)==1:
                concept_id=matches[0]['concept_id']
            elif len(matches)==0:
                concept_id=allocate(normalized,concept_type)
            else:
                typed=[x for x in matches if x['concept_type']==concept_type]
                if len(typed)!=1:
                    raise ValueError(f'ambiguous concept identity for {field}/{normalized}: {matches}')
                concept_id=typed[0]['concept_id']
            used.add(concept_id)
            binding={'field':field,'source_normalized':normalized,'concept_id':concept_id}
            registry['source_bindings'].append(binding); by_binding[key]=concept_id; bindings_added.append(binding)

registry['allocation']['next_sequence']=next_sequence
batch_created=[x for x in registry['concepts'] if any(h.get('batch_id')==BATCH_ID and h.get('event')=='created_from_approved_semantic_card' for h in x.get('history',[]))]
batch_created_ids={x['concept_id'] for x in batch_created}
event={'batch_id':BATCH_ID,'event':'approved_semantic_delta_applied','new_concept_ids':sorted(batch_created_ids),
       'new_relations':0,'requires_semantic_approval':0,'source_file':'source-cards/RK17_0105_0132_approved.json'}
if not any(x.get('batch_id')==BATCH_ID and x.get('event')==event['event'] for x in registry['migration_log']):
    registry['migration_log'].append(event)
registry['concepts'].sort(key=lambda x:x['concept_id'])
registry['source_bindings'].sort(key=lambda x:(x['field'],x['source_normalized'],x['concept_id']))
write_json(REGISTRY,registry)
write_json(ROOT/'rk17_0105_0132_registry_delta.json',{
    'batch_id':BATCH_ID,'existing_concept_ids_used':sorted(used-batch_created_ids),
    'new_concepts':sorted(batch_created,key=lambda x:x['concept_id']),
    'new_relations':[],'requires_semantic_approval':[],
    'untyped_search_semantics_policy':'Preserved verbatim in semantic cards and lexical Search; not converted into typed concepts without an approved field assignment.',
    'source_bindings_added':bindings_added,
})
print(json.dumps({'created_for_batch':len(batch_created),'existing_used':len(used-batch_created_ids),'bindings_added_now':len(bindings_added),'next_sequence':next_sequence},ensure_ascii=False))
