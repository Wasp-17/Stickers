"""Build the browser catalog from approved semantic cards and concept bindings."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'catalog-data'

def load(name):
    return json.loads((DATA / name).read_text(encoding='utf-8'))

cards = load('semantic_cards.json')['records']
bindings = load('image_concept_bindings.json')['bindings']
dictionary = load('global_search_dictionary.v1.json')
characters = load('character_registry.json')
by_binding = {x['image_id']: x['fields'] for x in bindings}
concepts = {x['concept_id']: x for x in dictionary['concepts']}
character = next(x for x in characters['characters'] if x['character_id'] == 'RK17')

entries = [{
    'image_id': 'TRANSFORMER-LOCAL',
    'display_name': 'Грозный Трансформер',
    'src': 'images/ChatGPT Image 6 сент. 2026 г., 23_18_15.png',
    'sections': ['ТРАНСФОРМЕРЫ'],
    'character_id': None,
    'character_name': None,
    'field_concepts': {},
    'concept_ids': [],
    'search_text': ['Грозный Трансформер', 'трансформер'],
    'semantic_status': 'local_preview_only',
}]

search_fields = ['display_name','primary_subjects','secondary_subjects','role','mood','themes','scenario','actions','objects','clothing','decorations','intent','search_aliases','search_semantics']
for card in cards:
    image_id = card['image_id']
    if not image_id.startswith('RK17-'):
        continue
    src = ROOT / 'images' / f'{image_id}_WEB.webp'
    if not src.exists():
        raise FileNotFoundError(src)
    fields = by_binding[image_id]
    field_concepts = {field: list(dict.fromkeys(x['concept_id'] for x in values)) for field, values in fields.items()}
    concept_ids = list(dict.fromkeys(concept_id for values in field_concepts.values() for concept_id in values))
    text = [card['display_name'], character['public_name'], image_id]
    for field in search_fields:
        value = card.get(field)
        if isinstance(value, list):
            text.extend(str(x) for x in value)
        elif value:
            text.append(str(value))
    entries.append({
        'image_id': image_id,
        'display_name': card['display_name'],
        'src': f'images/{image_id}_WEB.webp',
        'sections': card.get('sections', []),
        'character_id': 'RK17',
        'character_name': character['public_name'],
        'field_concepts': field_concepts,
        'concept_ids': concept_ids,
        'search_text': list(dict.fromkeys(text)),
        'semantic_status': card['semantic_status'],
    })

expected_rk17 = ({f'RK17-{i:04d}' for i in range(1, 76)} |
                 {f'RK17-{i:04d}' for i in range(91, 133)})
assert {entry['image_id'] for entry in entries if entry['image_id'].startswith('RK17-')} == expected_rk17
used = {concept_id for entry in entries for concept_id in entry['concept_ids']}
assert used <= set(concepts)

filters = {
    'sections': sorted({value for entry in entries for value in entry['sections']}),
    'characters': [{'value':'RK17','label':character['public_name']}],
    'roles': sorted(({'value':concept_id,'label':concepts[concept_id]['canonical']} for concept_id in {value for entry in entries for value in entry['field_concepts'].get('role',[])}), key=lambda x:x['label']),
    'moods': sorted(({'value':concept_id,'label':concepts[concept_id]['canonical']} for concept_id in {value for entry in entries for value in entry['field_concepts'].get('mood',[])}), key=lambda x:x['label']),
}

output = {
    'schema_version':'site_catalog_1.0',
    'status':'approved_dictionary_connected',
    'dictionary_version':dictionary['version'],
    'search_execution':{
        'catalog_changes_only_on_submit':True,
        'submit_triggers':['ENTER','APPLY_BUTTON'],
        'structured_filter_combination':'AND',
        'section_is_required':True,
    },
    'entry_count':len(entries),
    'filters':filters,
    'entries':entries,
}
(DATA / 'site_catalog.json').write_text(json.dumps(output,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({'entries':len(entries),'rk17':len(entries)-1,'filters':{k:len(v) for k,v in filters.items()}},ensure_ascii=False,indent=2))
