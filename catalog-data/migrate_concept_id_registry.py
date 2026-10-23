"""One-time migration from the reviewed legacy dictionary to a permanent ID registry.

The registry, once created, is authoritative. Future builds must never recreate it
from canonical text. New IDs are allocated sequentially and then persisted.
"""
import json
from pathlib import Path
import unicodedata

ROOT = Path(__file__).resolve().parent
OLD_DICTIONARY = ROOT / 'migration-source' / 'legacy_dictionary.pre_id_registry.json'
OLD_BINDINGS = ROOT / 'migration-source' / 'legacy_bindings.pre_id_registry.json'
REGISTRY = ROOT / 'concept_id_registry.json'
MIGRATION = ROOT / 'concept_id_migration.json'

def norm(value):
    return ' '.join(unicodedata.normalize('NFC', value).strip().upper().split())

def allocate(registry, canonical, concept_type, sense_key):
    """Allocate a persistent ID unrelated to canonical text or concept type."""
    if any(x['sense_key'] == sense_key for x in registry['concepts']):
        raise ValueError(f'duplicate sense_key: {sense_key}')
    number = registry['allocation']['next_sequence']
    registry['allocation']['next_sequence'] += 1
    concept_id = f'GSC-{number:06d}'
    registry['concepts'].append({
        'concept_id': concept_id,
        'sense_key': sense_key,
        'canonical': norm(canonical),
        'concept_type': concept_type,
        'lifecycle': 'active',
        'history': [{'event':'created', 'reason':'explicit_registry_allocation'}],
    })
    return concept_id

if REGISTRY.exists():
    raise SystemExit('concept_id_registry.json already exists; refusing to replace permanent IDs')

dictionary = json.loads(OLD_DICTIONARY.read_text(encoding='utf-8'))
bindings = json.loads(OLD_BINDINGS.read_text(encoding='utf-8'))['bindings']
registry = {
    'schema_version': 'concept_id_registry_1.0',
    'status': 'approved',
    'authority': 'Permanent concept identity and source-field resolution.',
    'identity_rules': {
        'concept_id_is_immutable': True,
        'canonical_rename_preserves_id': True,
        'concept_type_change_preserves_id': True,
        'concept_id_prefix_is_historical': True,
        'concept_id_prefix_does_not_define_current_concept_type': True,
        'concept_type_source_of_truth': 'concept_type',
        'consumers_must_not_infer_type_from_concept_id': True,
        'same_spelling_does_not_imply_same_concept': True,
        'different_source_fields_do_not_imply_different_concepts': True,
        'source_resolution': 'Exact field + normalized source text resolves through source_bindings. Multiple senses may share canonical text and require distinct sense_key values.',
        'unknown_binding': 'Fail build and require explicit registry migration; never synthesize an ID.',
    },
    'allocation': {'prefix':'GSC', 'next_sequence':1, 'derived_from_canonical_or_type':False},
    'concepts': [],
    'source_bindings': [],
    'migration_log': [],
}
for old in dictionary['concepts']:
    registry['concepts'].append({
        'concept_id': old['concept_id'],
        'sense_key': 'LEGACY_' + old['concept_id'],
        'canonical': old['canonical'],
        'concept_type': old['concept_type'],
        'lifecycle': 'active',
        'history': [{'event':'migrated', 'from':'hash-era dictionary', 'id_preserved':True}],
    })
by_id = {x['concept_id']:x for x in registry['concepts']}
by_name = {(x['canonical'],x['concept_type']):x for x in registry['concepts']}

raw_bindings = {}
for image in bindings:
    for field, entries in image['fields'].items():
        for entry in entries:
            key = (field, norm(entry['source_value']))
            old = raw_bindings.setdefault(key, entry['concept_id'])
            if old != entry['concept_id']:
                raise ValueError(f'ambiguous legacy binding {key}: {old}, {entry["concept_id"]}')

renames = {
    ('АРТЕФАКТ/ОСТАНКИ','OBJECT'):'ДРЕВНЯЯ НАХОДКА',
    ('БАБОЧКА','CLOTHING'):'ГАЛСТУК-БАБОЧКА',
    ('КОНЬ','OBJECT'):'ШАХМАТНЫЙ КОНЬ',
    ('МИР','THEME'):'ОКРУЖАЮЩИЙ МИР',
    ('КИСТЬ','OBJECT'):'КИСТЬ (ИНСТРУМЕНТ)',
}
retypes = {
    ('ОЧКИ','OBJECT'):'CLOTHING',
    ('ТЁМНЫЕ ОЧКИ','OBJECT'):'CLOTHING',
    ('СОЛНЕЧНЫЕ ОЧКИ','OBJECT'):'CLOTHING',
    ('ШЛЯПА','OBJECT'):'CLOTHING',
}
changed = []
for key, new_name in renames.items():
    item = by_name[key]
    old_name = item['canonical']
    item['canonical'] = new_name
    item['history'].append({'event':'canonical_renamed', 'from':old_name, 'to':new_name, 'id_preserved':True, 'reason':'approved_semantic_review'})
    changed.append({'concept_id':item['concept_id'], 'change':'canonical_renamed', 'from':old_name, 'to':new_name, 'id_preserved':True})
for key, new_type in retypes.items():
    item = by_name[key]
    old_type = item['concept_type']
    item['concept_type'] = new_type
    item['history'].append({'event':'concept_type_changed', 'from':old_type, 'to':new_type, 'id_preserved':True, 'reason':'approved_wearable_rule'})
    changed.append({'concept_id':item['concept_id'], 'change':'concept_type_changed', 'from':old_type, 'to':new_type, 'id_preserved':True})

# Morphological sentence variants resolve to one action sense, without a synonym edge.
survivor = by_name[('ИГРАТЬ В ФУТБОЛ','ACTION')]
retired = by_name[('ИГРАЮ В ФУТБОЛ','INTENT')]
retired['lifecycle'] = 'retired_redirect'
retired['redirect_to'] = survivor['concept_id']
retired['history'].append({'event':'merged', 'redirect_to':survivor['concept_id'], 'reason':'inflected first-person expression of the same football action'})
changed.append({'concept_id':retired['concept_id'], 'change':'retired_redirect', 'to_concept_id':survivor['concept_id'], 'id_preserved_as_redirect':True})
for key,value in list(raw_bindings.items()):
    if value == retired['concept_id']:
        raw_bindings[key] = survivor['concept_id']

# Approved raw-source corrections retain the existing IDs.
cosmonaut = by_name[('КОСМОНАВТ','ROLE')]['concept_id']
raw_bindings[('role','АСТРОНАВТ')] = cosmonaut
raw_bindings[('role','АСТРОНАВТ, КОСМОНАВТ')] = cosmonaut
raw_bindings[('objects','АРТЕФАКТ/ОСТАНКИ')] = by_name[('АРТЕФАКТ/ОСТАНКИ','OBJECT')]['concept_id']
raw_bindings[('clothing','БАБОЧКА')] = by_name[('БАБОЧКА','CLOTHING')]['concept_id']
raw_bindings[('objects','КОНЬ')] = by_name[('КОНЬ','OBJECT')]['concept_id']
raw_bindings[('themes','МИР')] = by_name[('МИР','THEME')]['concept_id']
raw_bindings[('intent','ИГРАЮ В ФУТБОЛ')] = survivor['concept_id']
# КИСТЬ and КИСТОЧКА are approved as one instrument sense. The lexical
# synonym remains in the graph, while both source forms bind to the canonical
# instrument concept.
raw_bindings[('objects','КИСТОЧКА')] = by_name[('КИСТЬ','OBJECT')]['concept_id']

# Approved normalized forms and the unified wearable rule. These aliases make
# the registry reusable after the source cards themselves have been migrated.
raw_bindings[('objects','ДРЕВНЯЯ НАХОДКА')] = by_name[('АРТЕФАКТ/ОСТАНКИ','OBJECT')]['concept_id']
raw_bindings[('clothing','ГАЛСТУК-БАБОЧКА')] = by_name[('БАБОЧКА','CLOTHING')]['concept_id']
raw_bindings[('objects','ШАХМАТНЫЙ КОНЬ')] = by_name[('КОНЬ','OBJECT')]['concept_id']
raw_bindings[('themes','ОКРУЖАЮЩИЙ МИР')] = by_name[('МИР','THEME')]['concept_id']
raw_bindings[('objects','КИСТЬ (ИНСТРУМЕНТ)')] = by_name[('КИСТЬ','OBJECT')]['concept_id']
for wearable in ('ШЛЯПА','ПОЛЕВАЯ ШЛЯПА','ОЧКИ','ЗАЩИТНЫЕ ОЧКИ','ТЁМНЫЕ ОЧКИ','СОЛНЕЧНЫЕ ОЧКИ'):
    matches = [x for x in registry['concepts'] if x['canonical'] == wearable and x['lifecycle'] == 'active']
    if len(matches) != 1:
        raise ValueError(f'wearable registry resolution is not unique: {wearable}: {matches}')
    raw_bindings[('clothing',wearable)] = matches[0]['concept_id']

registry['source_bindings'] = [
    {'field':field, 'source_normalized':source, 'concept_id':concept_id}
    for (field,source),concept_id in sorted(raw_bindings.items())
]
registry['migration_log'] = changed

active = [x for x in registry['concepts'] if x['lifecycle']=='active']
assert len({x['concept_id'] for x in registry['concepts']}) == len(registry['concepts'])
assert len({x['sense_key'] for x in registry['concepts']}) == len(registry['concepts'])
assert all(x['concept_id'] in by_id for x in registry['source_bindings'])
assert all(by_id[x['concept_id']]['lifecycle']=='active' for x in registry['source_bindings'])

REGISTRY.write_text(json.dumps(registry,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8',newline='\n')
MIGRATION.write_text(json.dumps({
    'schema_version':'concept_id_migration_1.0',
    'status':'approved',
    'source_dictionary':'migration-source/legacy_dictionary.pre_id_registry.json',
    'source_bindings':'migration-source/legacy_bindings.pre_id_registry.json',
    'preserved_active_ids':len(active),
    'changed_concept_ids':changed,
    'remaining_requires_semantic_approval':['ОБРАЗ МИРА'],
},ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({'registry_concepts':len(registry['concepts']), 'active':len(active), 'source_bindings':len(registry['source_bindings']), 'changed':len(changed)},ensure_ascii=False,indent=2))
