"""Independent integrity checks for the pending Global Search Dictionary build."""
import json
import hashlib
import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def load(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))

dictionary = load('global_search_dictionary.v1.json')
registry = load('concept_id_registry.json')
migration = load('concept_id_migration.json')
cards = load('semantic_cards.json')
bindings = load('image_concept_bindings.json')
characters = load('image_character_links.json')
legacy = load('migration-source/legacy_dictionary.pre_id_registry.json')
site_catalog = load('site_catalog.json')
batch_delta = load('rk17_0091_0104_registry_delta.json')
production_delta = load('rk17_0105_0132_registry_delta.json')
asset_import = load('rk17_web_asset_import.json')
technical_registry = load('image_registry.json')
image_sequence = load('image_id_sequence.json')

for source in dictionary['sources']:
    raw = (ROOT / source['file']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == source['sha256']

assert dictionary['status'] == registry['status'] == migration['status'] == 'approved'
assert bindings['status'] == 'approved'
assert site_catalog['status'] == 'approved_dictionary_connected'
assert site_catalog['dictionary_version'] == dictionary['version']
assert site_catalog['search_execution']['catalog_changes_only_on_submit'] is True
assert site_catalog['search_execution']['structured_filter_combination'] == 'AND'
assert site_catalog['search_execution']['section_is_required'] is True
assert len(site_catalog['entries']) == 118
assert len(cards['records']) == len(bindings['bindings']) == 132
assert len({x['image_id'] for x in cards['records']}) == 132

# Reconstruct the only approved card edits from the immutable source snapshots.
raw_cards = load('source-cards/RK17_semantic_metadata_1_2.json')['records']
for filename in ['OTHER_0076_0080_manifest.json','OTHER_0081_0088_manifest.json','OTHER_0089_0090_manifest.json']:
    raw_cards += load('source-cards/' + filename)['items']
approved_batch = load('source-cards/RK17_0091_0104_approved.json')
raw_cards += [{**approved_batch['common_fields'], **item} for item in approved_batch['records']]
raw_cards += load('source-cards/RK17_0105_0132_approved.json')['records']
renames = {
    ('role','АСТРОНАВТ'):'КОСМОНАВТ', ('role','АСТРОНАВТ, КОСМОНАВТ'):'КОСМОНАВТ',
    ('objects','АРТЕФАКТ/ОСТАНКИ'):'ДРЕВНЯЯ НАХОДКА', ('clothing','БАБОЧКА'):'ГАЛСТУК-БАБОЧКА',
    ('objects','КОНЬ'):'ШАХМАТНЫЙ КОНЬ', ('themes','МИР'):'ОКРУЖАЮЩИЙ МИР',
    ('objects','КИСТЬ'):'КИСТЬ (ИНСТРУМЕНТ)', ('objects','КИСТОЧКА'):'КИСТЬ (ИНСТРУМЕНТ)',
}
wearables = {'ШЛЯПА','ПОЛЕВАЯ ШЛЯПА','ОЧКИ','ЗАЩИТНЫЕ ОЧКИ','ТЁМНЫЕ ОЧКИ','СОЛНЕЧНЫЕ ОЧКИ'}
def normalized(value):
    return ' '.join(value.strip().upper().split())
expected_cards = []
for source in raw_cards:
    expected = copy.deepcopy(source)
    role_key = ('role', normalized(source['role'])) if isinstance(source.get('role'),str) else None
    if role_key in renames:
        expected['role'] = renames[role_key]
    elif isinstance(source.get('role'),list):
        expected['role'] = source['role'][0] if len(source['role']) == 1 else source['role']
    for field in ['themes','objects','clothing']:
        values = []
        for value in source.get(field, []):
            key = (field, normalized(value))
            if field == 'objects' and normalized(value) in wearables:
                continue
            replacement = renames.get(key, value)
            if replacement not in values:
                values.append(replacement)
        if field in source or values:
            expected[field] = values
    moved = [value for value in source.get('objects',[]) if normalized(value) in wearables]
    if moved:
        expected['clothing'] = list(dict.fromkeys(moved + expected.get('clothing',[])))
    expected_cards.append(expected)
assert cards['records'] == expected_cards

records = registry['concepts']
active = {x['concept_id']: x for x in records if x['lifecycle'] == 'active'}
all_ids = {x['concept_id'] for x in records}
concepts = {x['concept_id']: x for x in dictionary['concepts']}
assert len(all_ids) == len(records)
assert len({x['sense_key'] for x in records}) == len(records)
assert set(concepts) == set(active)
assert registry['allocation']['derived_from_canonical_or_type'] is False
assert registry['identity_rules']['concept_id_is_immutable'] is True
assert registry['identity_rules']['canonical_rename_preserves_id'] is True
assert registry['identity_rules']['concept_type_change_preserves_id'] is True
assert registry['identity_rules']['concept_id_prefix_is_historical'] is True
assert registry['identity_rules']['concept_id_prefix_does_not_define_current_concept_type'] is True
assert registry['identity_rules']['concept_type_source_of_truth'] == 'concept_type'
assert registry['identity_rules']['consumers_must_not_infer_type_from_concept_id'] is True
assert registry['identity_rules']['same_spelling_does_not_imply_same_concept'] is True
assert registry['identity_rules']['different_source_fields_do_not_imply_different_concepts'] is True

source_keys = set()
for item in registry['source_bindings']:
    key = (item['field'], item['source_normalized'])
    assert key not in source_keys
    source_keys.add(key)
    assert item['concept_id'] in active

legacy_by_id = {x['concept_id']: x for x in legacy['concepts']}
for change in migration['changed_concept_ids']:
    concept_id = change['concept_id']
    assert concept_id in legacy_by_id
    if change['change'] == 'canonical_renamed':
        assert legacy_by_id[concept_id]['canonical'] == change['from']
        assert active[concept_id]['canonical'] == change['to']
        assert change['id_preserved'] is True
    elif change['change'] == 'concept_type_changed':
        assert legacy_by_id[concept_id]['concept_type'] == change['from']
        assert active[concept_id]['concept_type'] == change['to']
        assert change['id_preserved'] is True
    else:
        assert change['change'] == 'retired_redirect'
        retired = next(x for x in records if x['concept_id'] == concept_id)
        assert retired['lifecycle'] == 'retired_redirect'
        assert retired['redirect_to'] == change['to_concept_id']

def one(name, kind=None):
    matches = [x for x in concepts.values() if x['canonical'] == name and (kind is None or x['concept_type'] == kind)]
    assert len(matches) == 1, (name, kind, matches)
    return matches[0]['concept_id']

def has_edge(a, relation, b, constraint=False):
    matches = [x for x in dictionary['relations'] if x['from'] == a and x['relation'] == relation and x['to'] == b]
    if constraint:
        matches = [x for x in matches if x.get('constraints')]
    assert len(matches) == 1, (a, relation, b, matches)
    return matches[0]

# Approved resolutions and the only remaining unresolved case.
assert [x['concept_a'] for x in dictionary['REQUIRES_SEMANTIC_APPROVAL']] == ['ОБРАЗ МИРА']
assert migration['remaining_requires_semantic_approval'] == ['ОБРАЗ МИРА']
assert sum(x['status'] == 'requires_semantic_approval' for x in concepts.values()) == 1
assert next(x for x in concepts.values() if x['status'] == 'requires_semantic_approval')['canonical'] == 'ОБРАЗ МИРА'
assert all(x['status'] in {'approved','requires_semantic_approval'} for x in concepts.values())
for name, kind in [('ДРЕВНЯЯ НАХОДКА','OBJECT'), ('ГАЛСТУК-БАБОЧКА','CLOTHING'),
                   ('ШАХМАТНЫЙ КОНЬ','OBJECT'), ('ОКРУЖАЮЩИЙ МИР','THEME')]:
    one(name, kind)
for left, kind, right in [('ТУРИСТ','ROLE','ПУТЕШЕСТВЕННИК'),
                          ('ДОВОЛЬСТВО','MOOD','УДОВЛЕТВОРЕНИЕ'),
                          ('СПОКОЙСТВИЕ','MOOD','УМИРОТВОРЕНИЕ')]:
    has_edge(one(left,kind), 'RELATED', one(right,kind))

# Developer/programmer equivalence is conditional and never duplicated unconditionally.
programmer = one('ПРОГРАММИСТ','ROLE')
developer = one('РАЗРАБОТЧИК','ROLE')
dev_edges = [x for x in dictionary['relations'] if {x['from'],x['to']} == {programmer,developer}]
assert len(dev_edges) == 1
dev = has_edge(programmer, 'SYNONYM', developer, constraint=True)
assert dev['constraints']['scope'] == 'software_developer'
assert dev['constraints']['bidirectional_only_when_scope_matches'] is True
assert dev['constraints']['unscoped_synonym_forbidden'] is True
assert len(dev['constraints']['context_any_concept_ids']) >= 1

# Morphology resolves both forms to a single ACTION identity.
football = one('ИГРАТЬ В ФУТБОЛ','ACTION')
assert not any(x['canonical'] == 'ИГРАЮ В ФУТБОЛ' for x in concepts.values())
resolution = dictionary['rules']['morphology_resolutions']
assert len(resolution) == 1 and resolution[0]['surface'] == 'ИГРАЮ В ФУТБОЛ'
assert resolution[0]['concept_id'] == football and resolution[0]['creates_synonym_edge'] is False
football_sources = [x for x in registry['source_bindings'] if x['source_normalized'] in {'ИГРАЮ В ФУТБОЛ','ИГРАТЬ В ФУТБОЛ'}]
assert football_sources and {x['concept_id'] for x in football_sources} == {football}

# Brush forms share the instrument sense for image bindings and remain searchable synonyms.
brush = one('КИСТЬ (ИНСТРУМЕНТ)','OBJECT')
brush_synonym = one('КИСТОЧКА','OBJECT')
has_edge(brush, 'SYNONYM', brush_synonym)
brush_sources = [x for x in registry['source_bindings'] if x['field'] == 'objects' and x['source_normalized'] in {'КИСТЬ','КИСТОЧКА','КИСТЬ (ИНСТРУМЕНТ)'}]
assert {x['concept_id'] for x in brush_sources} == {brush}

# One wearable classification rule, with distinct dark and sunglasses concepts.
wearable_names = ['ШЛЯПА','ПОЛЕВАЯ ШЛЯПА','ОЧКИ','ЗАЩИТНЫЕ ОЧКИ','ТЁМНЫЕ ОЧКИ','СОЛНЕЧНЫЕ ОЧКИ']
wearable_ids = {name: one(name,'CLOTHING') for name in wearable_names}
assert wearable_ids['ТЁМНЫЕ ОЧКИ'] != wearable_ids['СОЛНЕЧНЫЕ ОЧКИ']
for child in ['ЗАЩИТНЫЕ ОЧКИ','ТЁМНЫЕ ОЧКИ','СОЛНЕЧНЫЕ ОЧКИ']:
    has_edge(wearable_ids[child], 'BROADER', wearable_ids['ОЧКИ'])
has_edge(wearable_ids['ПОЛЕВАЯ ШЛЯПА'], 'BROADER', wearable_ids['ШЛЯПА'])
assert dictionary['rules']['object_clothing_policy']['verified_concepts'] == wearable_ids

# Approved hard constraints are executable flags, not prose-only notes.
hard = dictionary['rules']['hard_constraints']
assert hard['explicit_substantial_theme_may_be_hard'] is True
assert hard['primary_secondary_subjects_interchangeable'] is False
assert hard['secondary_subject_cannot_satisfy_required_primary_subject'] is True
assert hard['required_species_may_be_replaced_by_sibling_species'] is False
assert hard['related_edge_can_confirm_factual_presence'] is False
assert hard['related_edge_can_satisfy_required_object_theme_or_role'] is False
assert dictionary['rules']['style_coverage']['status'] == 'absent_in_source_cards'
assert dictionary['rules']['style_coverage']['requires_semantic_approval'] is False

# The serialization contract is explicit and verified on every generated file.
repro = dictionary['rules']['reproducibility']
assert repro['semantic_json_reproducibility'] is True
assert repro['encoding'] == 'UTF-8 without BOM' and repro['newline'] == 'LF'
assert repro['json_key_order'] == 'lexicographic (sort_keys=true)'
assert repro['indent_spaces'] == 2 and repro['final_newline'] is True
for filename in ['concept_id_registry.json','concept_id_migration.json','semantic_cards.json',
                 'global_search_dictionary.v1.json','image_concept_bindings.json']:
    raw = (ROOT / filename).read_bytes()
    assert not raw.startswith(b'\xef\xbb\xbf') and b'\r\n' not in raw and raw.endswith(b'\n')
    parsed = json.loads(raw.decode('utf-8'))
    expected = (json.dumps(parsed,ensure_ascii=False,indent=2,sort_keys=True)+'\n').encode('utf-8')
    assert raw == expected
report_raw = (ROOT / 'GLOBAL_SEARCH_DICTIONARY_REPORT.md').read_bytes()
assert not report_raw.startswith(b'\xef\xbb\xbf') and b'\r\n' not in report_raw and report_raw.endswith(b'\n')

# Historical prefixes are demonstrably independent from the current type.
assert any(x['concept_id'].startswith('OBJECT_') and x['concept_type'] == 'CLOTHING' for x in concepts.values())

# Character/subject hierarchy and image assignments remain exact.
person = one('ПЕРСОНАЖ','SUBJECT')
animal = one('ЖИВОТНОЕ','SUBJECT')
cat = one('КОТ','SUBJECT')
has_edge(cat, 'BROADER', animal)
assert not any({x['from'],x['to']} == {animal,person} for x in dictionary['relations'])
character = dictionary['character_bindings'][0]
assert character['entity_type'] == {'relation':'ENTITY_TYPE','concept_id':person}
assert character['species_subject'] == {'relation':'SPECIES_SUBJECT','concept_id':cat}
expected_character_links = ({f'RK17-{i:04d}' for i in range(1,76)} |
                            {f'RK17-{i:04d}' for i in range(91,133)})
assert len(characters['links']) == 117
assert {x['image_id'] for x in characters['links']} == expected_character_links
assert all(x['character_id'] == 'RK17' and x['assignment_status'] == 'approved' for x in characters['links'])
technical_ids = [x['image_id'] for x in technical_registry['images']]
assert len(technical_ids) == len(set(technical_ids)) == 117
assert set(technical_ids) == expected_character_links
sequence_numbers = [x['number'] for x in image_sequence['assignments']]
sequence_ids = [x['image_id'] for x in image_sequence['assignments']]
assert len(sequence_numbers) == len(set(sequence_numbers)) == 132
assert len(sequence_ids) == len(set(sequence_ids)) == 132
assert image_sequence['last_assigned_number'] == 132 and image_sequence['next_available_number'] == 133

# RK17-0091..0104 is an approved, relation-free delta. Its WEB assets are the
# only production variants exposed by the site; ART and MASTER remain in source archives.
batch_ids = {f'RK17-{i:04d}' for i in range(91,105)}
batch_cards = [x for x in cards['records'] if x['image_id'] in batch_ids]
assert len(batch_cards) == 14 and {x['image_id'] for x in batch_cards} == batch_ids
assert all(x['semantic_status'] == 'approved' and x['character_id'] == 'RK17' and x['public_name'] == 'Чеддер' for x in batch_cards)
assert all(x['role'] is None and x['primary_subjects'] == ['кот'] and x['secondary_subjects'] == [] for x in batch_cards)
assert batch_delta['batch_id'] == 'RK17-0091-0104'
assert len(batch_delta['new_concepts']) == 38
assert batch_delta['new_relations'] == [] and batch_delta['requires_semantic_approval'] == []
asset_by_id = {x['image_id']:x for x in asset_import['assets']}
assert batch_ids <= set(asset_by_id)
for image_id in batch_ids:
    public_file = ROOT.parent / 'images' / f'{image_id}_WEB.webp'
    assert public_file.is_file()
    assert hashlib.sha256(public_file.read_bytes()).hexdigest() == asset_by_id[image_id]['sha256']
assert not list((ROOT.parent / 'images').glob('RK17_*MASTER*'))

production_ids = {f'RK17-{i:04d}' for i in range(105,133)}
production_cards = [x for x in cards['records'] if x['image_id'] in production_ids]
assert len(production_cards) == 28 and {x['image_id'] for x in production_cards} == production_ids
assert all(x['semantic_status'] == 'approved' and x['character_id'] == 'RK17' and x['public_name'] == 'Чеддер' for x in production_cards)
assert production_delta['batch_id'] == 'RK17-0105-0132'
assert len(production_delta['new_concepts']) == 122
assert production_delta['new_relations'] == [] and production_delta['requires_semantic_approval'] == []
production_manifest = json.loads((ROOT.parent / 'production' / 'RK17-0105_0132_READY' / 'manifest.json').read_text(encoding='utf-8'))
assert len(production_manifest['items']) == 28
for item in production_manifest['items']:
    assert item['image_id'] in production_ids and item['rgb_pixels_verified'] is True
    assert item['requires_border_repair'] is False and item['decorative_white_border_removed'] is False
    for kind in ['art','master','web']:
        path = ROOT.parent / item[f'{kind}_path']
        assert path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == item[f'{kind}_sha256']

# Every emitted image binding points to an active concept and matches its field usage.
for image in bindings['bindings']:
    for field, entries in image['fields'].items():
        for entry in entries:
            assert entry['concept_id'] in active
            if field == 'clothing' and entry['normalized_card_value'].upper() in wearable_names:
                assert entry['concept_id'] == wearable_ids[entry['normalized_card_value'].upper()]

print(json.dumps({
    'status':'PASS',
    'review_status':dictionary['status'],
    'images':len(cards['records']),
    'active_concepts':len(active),
    'registry_records':len(records),
    'relations':len(dictionary['relations']),
    'changed_concept_ids':len(migration['changed_concept_ids']),
    'remaining_requires_semantic_approval':['ОБРАЗ МИРА'],
    'site_connected':True,
}, ensure_ascii=False, indent=2))
