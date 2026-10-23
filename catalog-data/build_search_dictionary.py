"""Build review artifacts from approved cards and a permanent concept registry."""
import collections
import copy
import hashlib
import json
from pathlib import Path
import unicodedata

OUT = Path(__file__).resolve().parent
SOURCE = OUT / 'source-cards'
REGISTRY_FILE = OUT / 'concept_id_registry.json'
MIGRATION_FILE = OUT / 'concept_id_migration.json'
TYPES = ['SUBJECT','ROLE','MOOD','THEME','ACTION','OBJECT','SCENARIO_CONCEPT','INTENT','CLOTHING','DECORATION','STYLE']
FIELDS = {'primary_subjects':'SUBJECT','secondary_subjects':'SUBJECT','role':'ROLE','mood':'MOOD','themes':'THEME','actions':'ACTION','objects':'OBJECT','clothing':'CLOTHING','decorations':'DECORATION','style':'STYLE','intent':'INTENT'}

def norm(value):
    return ' '.join(unicodedata.normalize('NFC', value).strip().upper().split())

sources = []
raw_records = []
def read_batch(filename, key):
    path = SOURCE / filename
    raw = path.read_bytes()
    sources.append({'file':f'source-cards/{filename}', 'sha256':hashlib.sha256(raw).hexdigest()})
    return json.loads(raw)[key]

raw_records += read_batch('RK17_semantic_metadata_1_2.json', 'records')
for filename in ['OTHER_0076_0080_manifest.json','OTHER_0081_0088_manifest.json','OTHER_0089_0090_manifest.json']:
    raw_records += read_batch(filename, 'items')
approved_batch = read_batch('RK17_0091_0104_approved.json', 'records')
approved_batch_file = json.loads((SOURCE / 'RK17_0091_0104_approved.json').read_text(encoding='utf-8'))
for item in approved_batch:
    raw_records.append({**approved_batch_file['common_fields'], **item})
raw_records += read_batch('RK17_0105_0132_approved.json', 'records')
expected_ids = ({f'RK17-{i:04d}' for i in range(1,76)} |
                {f'OTHER-{i:04d}' for i in range(76,91)} |
                {f'RK17-{i:04d}' for i in range(91,133)})
assert len(raw_records)==132 and {x['image_id'] for x in raw_records}==expected_ids

registry = json.loads(REGISTRY_FILE.read_text(encoding='utf-8'))
migration = json.loads(MIGRATION_FILE.read_text(encoding='utf-8'))
all_registry = {x['concept_id']:x for x in registry['concepts']}
active_registry = {k:v for k,v in all_registry.items() if v['lifecycle']=='active'}
source_resolution = {}
for item in registry['source_bindings']:
    key = (item['field'], item['source_normalized'])
    if key in source_resolution and source_resolution[key] != item['concept_id']:
        raise ValueError(f'ambiguous registry binding: {key}')
    source_resolution[key] = item['concept_id']

def resolve_source(field, value):
    key = (field, norm(value))
    if key not in source_resolution:
        raise KeyError(f'unknown source concept; explicit registry migration required: {key}')
    concept_id = source_resolution[key]
    if concept_id not in active_registry:
        raise ValueError(f'source binding points to inactive concept: {key} -> {concept_id}')
    return concept_id

def ref(canonical, concept_type=None, sense_key=None):
    matches = [x for x in active_registry.values() if x['canonical']==norm(canonical)]
    if concept_type is not None:
        matches = [x for x in matches if x['concept_type']==concept_type]
    if sense_key is not None:
        matches = [x for x in matches if x['sense_key']==sense_key]
    if len(matches)!=1:
        raise ValueError(f'explicit concept resolution required for {canonical!r}/{concept_type!r}/{sense_key!r}; matches={len(matches)}')
    return matches[0]['concept_id']

CARD_RENAMES = {
    ('role','АСТРОНАВТ'):'КОСМОНАВТ',
    ('role','АСТРОНАВТ, КОСМОНАВТ'):'КОСМОНАВТ',
    ('objects','АРТЕФАКТ/ОСТАНКИ'):'ДРЕВНЯЯ НАХОДКА',
    ('clothing','БАБОЧКА'):'ГАЛСТУК-БАБОЧКА',
    ('objects','КОНЬ'):'ШАХМАТНЫЙ КОНЬ',
    ('themes','МИР'):'ОКРУЖАЮЩИЙ МИР',
    ('objects','КИСТЬ'):'КИСТЬ (ИНСТРУМЕНТ)',
    ('objects','КИСТОЧКА'):'КИСТЬ (ИНСТРУМЕНТ)',
}
WEARABLES = {'ШЛЯПА','ПОЛЕВАЯ ШЛЯПА','ОЧКИ','ЗАЩИТНЫЕ ОЧКИ','ТЁМНЫЕ ОЧКИ','СОЛНЕЧНЫЕ ОЧКИ'}

def project(field, value):
    source = norm(value)
    target_field = 'clothing' if field=='objects' and source in WEARABLES else field
    target_value = CARD_RENAMES.get((field,source), value)
    resolution = None
    if (field,source)==('intent','ИГРАЮ В ФУТБОЛ'):
        resolution = 'first_person_intent_expression_of_action; resolves to ИГРАТЬ В ФУТБОЛ without a synonym concept'
    if target_field!=field:
        resolution = 'wearable_reclassified_from_OBJECT_to_CLOTHING'
    return target_field, target_value, resolution

records = []
bindings = []
card_changes = []
usage = collections.defaultdict(set)
for raw in raw_records:
    record = copy.deepcopy(raw)
    projected = {field:[] for field in FIELDS if field!='role'}
    role_values = []
    bound_fields = collections.defaultdict(list)
    for source_field in FIELDS:
        value = raw.get(source_field)
        terms = value if isinstance(value,list) else [value] if value else []
        for term in terms:
            concept_id = resolve_source(source_field, term)
            target_field, target_value, resolution = project(source_field, term)
            if target_field=='role':
                if target_value not in role_values:
                    role_values.append(target_value)
            elif target_value not in projected[target_field]:
                projected[target_field].append(target_value)
            entry = {'source_field':source_field,'source_value':term,'normalized_card_value':target_value,'concept_id':concept_id}
            if resolution:
                entry['resolution'] = resolution
            bound_fields[target_field].append(entry)
            usage[concept_id].add(target_field)
            if source_field!=target_field or norm(term)!=norm(target_value):
                card_changes.append({'image_id':raw['image_id'],'source_field':source_field,'target_field':target_field,'before':term,'after':target_value,'concept_id':concept_id})
    record['role'] = None if not role_values else role_values[0] if len(role_values)==1 else role_values
    for field,values in projected.items():
        if field in raw or values:
            record[field] = values
    scenario_key = ('scenario',norm(raw['scenario']))
    if scenario_key in source_resolution:
        concept_id = resolve_source('scenario',raw['scenario'])
        bound_fields['scenario'].append({'source_field':'scenario','source_value':raw['scenario'],'normalized_card_value':raw['scenario'],'concept_id':concept_id})
        usage[concept_id].add('scenario')
    records.append(record)
    bindings.append({'image_id':raw['image_id'],'fields':dict(bound_fields)})

concepts = []
for item in active_registry.values():
    concept = {'concept_id':item['concept_id'],'sense_key':item['sense_key'],'canonical':item['canonical'],'concept_type':item['concept_type'],'origin':'permanent_concept_id_registry','status':'approved'}
    if item['concept_id'] in usage:
        concept['used_in_fields'] = sorted(usage[item['concept_id']])
    if item['canonical']=='ОБРАЗ МИРА' and item['concept_type']=='OBJECT':
        concept['status'] = 'requires_semantic_approval'
    concepts.append(concept)
concepts.sort(key=lambda x:(x['concept_type'],x['canonical'],x['concept_id']))
concept_ids = {x['concept_id'] for x in concepts}

relations = []
def edge(a,at,relation,b,bt,basis='curated_direct_relation',constraints=None):
    item = {'from':ref(a,at),'relation':relation,'to':ref(b,bt),'basis':basis}
    if constraints is not None:
        item['constraints'] = constraints
    key = (item['from'],item['relation'],item['to'],json.dumps(item.get('constraints'),sort_keys=True,ensure_ascii=False))
    if not any((x['from'],x['relation'],x['to'],json.dumps(x.get('constraints'),sort_keys=True,ensure_ascii=False))==key for x in relations):
        relations.append(item)

for a,b in [('КОСМОНАВТ','АСТРОНАВТ'),('ПРОГРАММИСТ','КОДЕР'),('ДЕТЕКТИВ','СЫЩИК'),('ДИДЖЕЙ','DJ')]:
    edge(a,'ROLE','SYNONYM',b,'ROLE','approved_semantic_review')
edge('КИСТЬ (ИНСТРУМЕНТ)','OBJECT','SYNONYM','КИСТОЧКА','OBJECT','approved_semantic_review')
edge('ПРОГРАММИСТ','ROLE','SYNONYM','РАЗРАБОТЧИК','ROLE','approved_software_developer_scope',{
    'scope':'software_developer','bidirectional_only_when_scope_matches':True,'unscoped_synonym_forbidden':True,
    'context_any_concept_ids':[ref('IT','THEME'),ref('ПРОГРАММИРОВАНИЕ','THEME'),ref('КОД','OBJECT')],
})
for a,b in [('IT-СПЕЦИАЛИСТ','АЙТИШНИК'),('ПРОГРАММИСТ','ПРОГРАММЕР')]:
    edge(a,'ROLE','COLLOQUIAL',b,'ROLE','user_control_example')

broader = [
 ('КОТ','SUBJECT','ЖИВОТНОЕ','SUBJECT'),('СОБАКА','SUBJECT','ЖИВОТНОЕ','SUBJECT'),('ПТИЦА','SUBJECT','ЖИВОТНОЕ','SUBJECT'),
 ('ПРОГРАММИСТ','ROLE','IT-СПЕЦИАЛИСТ','ROLE'),('ГИТАРИСТ','ROLE','МУЗЫКАНТ','ROLE'),('ПЕВЕЦ','ROLE','МУЗЫКАНТ','ROLE'),
 ('ФУТБОЛИСТ','ROLE','СПОРТСМЕН','ROLE'),('БЕГУН','ROLE','СПОРТСМЕН','ROLE'),('ШЕФ-ПОВАР','ROLE','ПОВАР','ROLE'),
 ('НОУТБУК','OBJECT','КОМПЬЮТЕР','OBJECT'),
 ('ПОЛЕВАЯ ШЛЯПА','CLOTHING','ШЛЯПА','CLOTHING'),('ЗАЩИТНЫЕ ОЧКИ','CLOTHING','ОЧКИ','CLOTHING'),
 ('ТЁМНЫЕ ОЧКИ','CLOTHING','ОЧКИ','CLOTHING'),('СОЛНЕЧНЫЕ ОЧКИ','CLOTHING','ОЧКИ','CLOTHING'),
 ('БЕЛАЯ РУБАШКА','CLOTHING','РУБАШКА','CLOTHING'),('ЧЁРНЫЙ ДЕЛОВОЙ КОСТЮМ','CLOTHING','ДЕЛОВОЙ КОСТЮМ','CLOTHING'),
]
for a,at,b,bt in broader:
    edge(a,at,'BROADER',b,bt)
    edge(b,bt,'NARROWER',a,at)

groups = [
 ('КОСМОНАВТ','ROLE','THEME',['КОСМОС','КОСМИЧЕСКИЙ ПОЛЁТ']),('ПРОГРАММИСТ','ROLE','THEME',['ПРОГРАММИРОВАНИЕ','IT']),
 ('ПРОГРАММИСТ','ROLE','OBJECT',['КОД','КОМПЬЮТЕР','НОУТБУК']),('ТУРИСТ','ROLE','THEME',['ТУРИЗМ','ПУТЕШЕСТВИЕ','ПОХОД']),
 ('ТУРИСТ','ROLE','OBJECT',['РЮКЗАК']),('УЮТ','INTENT','OBJECT',['ДОМ','ГОРЯЧИЙ НАПИТОК']),('УЮТ','INTENT','THEME',['ОТДЫХ','ТЕПЛО','ЧТЕНИЕ']),
 ('ГИТАРИСТ','ROLE','OBJECT',['ГИТАРА']),('АРХЕОЛОГ','ROLE','THEME',['РАСКОПКИ','АРХЕОЛОГИЯ']),
 ('ПОВАР','ROLE','THEME',['КУЛИНАРИЯ','ПРИГОТОВЛЕНИЕ ЕДЫ']),('ПОВАР','ROLE','OBJECT',['СКОВОРОДА','КАСТРЮЛЯ']),
 ('ДЕТЕКТИВ','ROLE','THEME',['РАССЛЕДОВАНИЕ','ПОИСК УЛИК']),('ДЕТЕКТИВ','ROLE','OBJECT',['ЛУПА','УЛИКА']),
 ('ХУДОЖНИК','ROLE','THEME',['ЖИВОПИСЬ']),('ХУДОЖНИК','ROLE','OBJECT',['МОЛЬБЕРТ','ХОЛСТ']),
 ('ФУТБОЛИСТ','ROLE','THEME',['ФУТБОЛ']),('ФУТБОЛИСТ','ROLE','OBJECT',['ФУТБОЛЬНЫЙ МЯЧ']),
 ('ПЕВЕЦ','ROLE','OBJECT',['МИКРОФОН']),('ФОКУСНИК','ROLE','THEME',['ФОКУСЫ','ИЛЛЮЗИЯ']),
 ('ШАХМАТИСТ','ROLE','THEME',['ШАХМАТЫ']),('РОБОТОТЕХНИК','ROLE','THEME',['РОБОТОТЕХНИКА']),
 ('РОБОТОТЕХНИК','ROLE','OBJECT',['РОБОТ']),('ПУТЕШЕСТВЕННИК','ROLE','THEME',['ПУТЕШЕСТВИЕ']),
 ('БЕГУН','ROLE','THEME',['БЕГ']),('ДИДЖЕЙ','ROLE','OBJECT',['DJ-ПУЛЬТ']),
]
for a,at,bt,targets in groups:
    for b in targets:
        edge(a,at,'RELATED',b,bt)
for a,at,b,bt in [
    ('ТУРИСТ','ROLE','ПУТЕШЕСТВЕННИК','ROLE'),
    ('ДОВОЛЬСТВО','MOOD','УДОВЛЕТВОРЕНИЕ','MOOD'),
    ('СПОКОЙСТВИЕ','MOOD','УМИРОТВОРЕНИЕ','MOOD'),
]:
    edge(a,at,'RELATED',b,bt,'approved_semantic_review')
for a,b in [('ХИМИЧЕСКИЙ ЭКСПЕРИМЕНТ','ХИМИЯ'),('КАРТОЧНЫЙ ФОКУС','ФОКУСЫ'),('ФОКУС С МОНЕТОЙ','ФОКУСЫ'),('ЧТЕНИЕ У КАМИНА','ЧТЕНИЕ'),('ОТДЫХ В ГАМАКЕ','ОТДЫХ')]:
    edge(a,'SCENARIO_CONCEPT','RELATED',b,'THEME')

remaining_approval = [{
    'concept_id':ref('ОБРАЗ МИРА','OBJECT'),'concept_a':'ОБРАЗ МИРА','concept_b':None,'proposed_relation':'CANONICAL_SENSE',
    'reason':'Не определено, является ли это самостоятельным объектом, изображением планеты или представлением об окружающем мире.',
}]
football_action = ref('ИГРАТЬ В ФУТБОЛ','ACTION')
wearable_expectations = {x:ref(x,'CLOTHING') for x in ['ШЛЯПА','ПОЛЕВАЯ ШЛЯПА','ОЧКИ','ЗАЩИТНЫЕ ОЧКИ','ТЁМНЫЕ ОЧКИ','СОЛНЕЧНЫЕ ОЧКИ']}
dictionary = {
 'version':'1.0','status':'approved','architecture_revision':'1.2','allowed_concept_types':TYPES,'sources':sources,
 'concept_id_registry':'concept_id_registry.json','concept_id_migration':'concept_id_migration.json',
 'rules':{
  'authority':'This JSON is the dictionary source of truth. Markdown report is derived.',
  'concept_identity':registry['identity_rules'],'precedence':['DIRECT','SYNONYM','COLLOQUIAL','BROADER/NARROWER','RELATED'],
  'reproducibility':{
   'semantic_json_reproducibility':True,
   'byte_reproducibility_scope':'Generated JSON and Markdown outputs, given identical source files and the same generator version; archive container bytes are excluded.',
   'encoding':'UTF-8 without BOM','newline':'LF','json_key_order':'lexicographic (sort_keys=true)',
   'array_order':'deterministic generator order','indent_spaces':2,'final_newline':True,
  },
  'numeric_weights':None,'morphology':'Separate Search layer; grammatical forms do not create synonym concepts.',
  'expansion_depth':{'provisional_min':1,'provisional_max':2},
  'identity_model':'RK17 has ENTITY_TYPE PERSON and SPECIES_SUBJECT CAT; only CAT → ANIMAL belongs to the subject hierarchy.',
  'sections':'Never derive or mutate sections through semantic edges.',
  'structural_filters':'Exact canonical card values only; dictionary expansion is not used in dropdown matching.',
  'hard_constraints':{
   'eligible':['explicit_character','required_primary_subject_or_species','explicit_substantial_theme'],
   'explicit_substantial_theme_may_be_hard':True,'primary_secondary_subjects_interchangeable':False,
   'secondary_subject_cannot_satisfy_required_primary_subject':True,'broad_genus_query_may_include_narrower_species':True,
   'required_species_may_be_replaced_by_sibling_species':False,'related_edge_can_confirm_factual_presence':False,
   'related_edge_can_satisfy_required_object_theme_or_role':False,'apply_before_soft_expansion':True,
  },
  'object_clothing_policy':{
   'rule':'Wearable attire, accessories and protective wearable equipment are CLOTHING even when the source card placed them in objects. Standalone or hand-held scene items remain OBJECT.',
   'verified_concepts':wearable_expectations,
  },
  'morphology_resolutions':[{
   'surface':'ИГРАЮ В ФУТБОЛ','source_field':'intent','concept_id':football_action,'canonical':'ИГРАТЬ В ФУТБОЛ','concept_type':'ACTION',
   'semantic_note':'First-person user-intent expression of the same football action; the intent phrase remains in the card, but Search resolves it to the action concept.',
   'creates_synonym_edge':False,
  }],
  'style_coverage':{'status':'absent_in_source_cards','requires_semantic_approval':False,'instruction':'Do not infer style from pixels.'},
  'directionality':{'SYNONYM':'bidirectional only when relation constraints pass','COLLOQUIAL':'informal target resolves to source canonical','BROADER':'narrow to broad','NARROWER':'broad to narrow','RELATED':'bidirectional relevance only; never evidence of factual presence'},
 },
 'character_bindings':[{'character_id':'RK17','public_name':'Чеддер','entity_type':{'relation':'ENTITY_TYPE','concept_id':ref('ПЕРСОНАЖ','SUBJECT')},'species_subject':{'relation':'SPECIES_SUBJECT','concept_id':ref('КОТ','SUBJECT')},'registry_file':'character_registry.json','image_links_file':'image_character_links.json'}],
 'concepts':concepts,'relations':relations,'REQUIRES_SEMANTIC_APPROVAL':remaining_approval,
}

def write(name,obj):
    (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8',newline='\n')
write('semantic_cards.json',{'schema_version':'semantic_cards_1.2','sources':sources,'approved_changes':card_changes,'records':records})
write('global_search_dictionary.v1.json',dictionary)
write('image_concept_bindings.json',{'status':'approved','dictionary_file':'global_search_dictionary.v1.json','cards_file':'semantic_cards.json','concept_id_registry':'concept_id_registry.json','scenario_policy':'Raw scenario text retained. Eight direct scene abstractions are linked where explicitly defined.','bindings':bindings})
write('image_character_links.json',{
    'schema_version':'image_character_links_1.0',
    'architecture_revision':'1.2 current edition 2026-09-20',
    'character_registry_file':'character_registry.json',
    'assignment_rule':'Only images explicitly approved with character = RK17 are linked. OTHER images are excluded.',
    'links':[{'image_id':x['image_id'],'character_id':'RK17','assignment_status':'approved'}
             for x in records if x['image_id'].startswith('RK17-')],
})

assert len(concept_ids)==len(concepts)
assert all(x['concept_type'] in TYPES for x in concepts)
assert all(x['from'] in concept_ids and x['to'] in concept_ids for x in relations)
assert all(y['concept_id'] in concept_ids for x in bindings for entries in x['fields'].values() for y in entries)
assert len({x['image_id'] for x in bindings})==len(raw_records)
assert len(remaining_approval)==1 and remaining_approval[0]['concept_a']=='ОБРАЗ МИРА'
assert all(x.get('role') not in ('АСТРОНАВТ','АСТРОНАВТ, КОСМОНАВТ') for x in records)
assert {x['role'] for x in records if x['image_id'] in {'RK17-0001','RK17-0002','RK17-0003','OTHER-0081'}}=={'КОСМОНАВТ'}
assert active_registry[football_action]['concept_type']=='ACTION'
animal,person=ref('ЖИВОТНОЕ','SUBJECT'),ref('ПЕРСОНАЖ','SUBJECT')
assert not any(x['from']==animal and x['to']==person and x['relation']=='BROADER' for x in relations)
assert not any(x['from']==person and x['to']==animal and x['relation']=='NARROWER' for x in relations)
adj=collections.defaultdict(list)
for x in relations:
    if x['relation']=='BROADER':adj[x['from']].append(x['to'])
def visit(node,trail):
    assert node not in trail, 'BROADER hierarchy cycle'
    for target in adj[node]:visit(target,trail|{node})
for node in list(adj):visit(node,set())

counts=collections.Counter(x['concept_type'] for x in concepts)
relcounts=collections.Counter(x['relation'] for x in relations)
lookup={x['concept_id']:x['canonical'] for x in concepts}
report=['# Global Search Dictionary v1.0 — migration and integrity report','',
 '**Статус: approved. ОБРАЗ МИРА остаётся единственным pending semantic case. Сайт подключён через производный site_catalog.json.**','',
 f'Прочитаны {len(records)} карточки. Активных concepts: {len(concepts)}. Связей: {len(relations)}. Постоянных записей ID registry: {len(registry["concepts"])}.','',
 '## Исправления этого ревью','',
 '- Утверждённые решения перенесены в карточки, registry, bindings и граф.',
 '- Единственный оставшийся REQUIRES_SEMANTIC_APPROVAL — ОБРАЗ МИРА.',
 '- concept_id выдаёт только постоянный registry; rename и retype сохраняют ID.',
 '- Source bindings разрешают одинаковое написание в разные concepts и один concept из разных полей.',
 '- РАЗРАБОТЧИК ↔ ПРОГРАММИСТ записан как условный SYNONYM со scope software_developer.',
 '- ИГРАЮ В ФУТБОЛ разрешается в ACTION ИГРАТЬ В ФУТБОЛ без второго морфологического concept.',
 '- Правило OBJECT/CLOTHING применено к шляпам и очкам.',
 '- Hard constraints записаны машинно-читаемо в rules.hard_constraints.','',
 '## Stable concept_id','',
 '- Префикс concept_id — историческая часть неизменяемого ID и не определяет текущий concept_type.',
 '- Источник истины о типе — только поле concept_type.',
 '- Импорт, фильтрация и Search не должны выводить тип из префикса concept_id.',
 '- Поэтому ID вида OBJECT_… после утверждённого retype может иметь concept_type CLOTHING.','',
 '## Воспроизводимость','',
 '- Повторная сборка гарантирует идентичную JSON-структуру и данные при одинаковых исходных файлах и версии генератора.',
 '- Для генерируемых JSON и Markdown также зафиксированы UTF-8 без BOM, LF, лексикографический порядок ключей JSON, детерминированный порядок массивов, отступ 2 пробела и финальный LF.',
 '- Побайтовая идентичность контейнера ZIP не заявляется: метаданные архива могут зависеть от упаковщика.','',
 '## Количество concepts по типам','', '| Тип | Количество |','|---|---:|']
report += [f'| {t} | {counts[t]} |' for t in TYPES]
report += ['', '## Количество связей','', '| Связь | Количество |','|---|---:|']
report += [f'| {t} | {relcounts[t]} |' for t in ['SYNONYM','COLLOQUIAL','BROADER','NARROWER','RELATED']]
report += ['', '## Изменённые concept_id','']
for x in migration['changed_concept_ids']:
    if x['change']=='canonical_renamed':report.append(f"- {x['concept_id']}: canonical {x['from']} → {x['to']}; ID сохранён.")
    elif x['change']=='concept_type_changed':report.append(f"- {x['concept_id']}: concept_type {x['from']} → {x['to']}; ID сохранён.")
    else:report.append(f"- {x['concept_id']}: retired redirect → {x['to_concept_id']}.")
report += ['', '## Изменения semantic cards','']
for x in card_changes:
    arrow=x['source_field'] if x['source_field']==x['target_field'] else f"{x['source_field']} → {x['target_field']}"
    report.append(f"- {x['image_id']}: {arrow}; {x['before']} → {x['after']} ({x['concept_id']}).")
report += ['', '## Все канонические concepts','', '| concept_id | canonical | concept_type | Статус |','|---|---|---|---|']
report += [f"| {x['concept_id']} | {x['canonical'].replace('|','/')} | {x['concept_type']} | {x['status']} |" for x in concepts]
for kind in ['SYNONYM','COLLOQUIAL','BROADER','NARROWER','RELATED']:
    report += ['',f'## Все {kind}','']
    for x in relations:
        if x['relation']!=kind:continue
        constraint=f"; constraints={json.dumps(x['constraints'],ensure_ascii=False,sort_keys=True)}" if 'constraints' in x else ''
        report.append(f"- {lookup[x['from']]} → {lookup[x['to']]} ({x['basis']}{constraint}).")
report += ['', '## REQUIRES_SEMANTIC_APPROVAL','',
 f"1. **ОБРАЗ МИРА** ({remaining_approval[0]['concept_id']}): {remaining_approval[0]['reason']}",'',
 '## Повторный integrity report','',
 f'- {len(records)} уникальных image_id; все исходные карточки импортированы.',
 '- Все нормализации перечислены выше; display_name, Sections, character_assignment и художественные файлы не менялись.',
 '- Все source-field bindings разрешаются через постоянный concept_id registry.',
 '- Registry допускает одинаковый canonical у разных sense_key и один concept_id для нескольких полей.',
 '- Неизвестное или неоднозначное понятие останавливает сборку; ID не вычисляется из canonical/type.',
 '- Все ссылки на active concept_id разрешены; ID и sense_key уникальны.',
 '- В BROADER нет циклов; ЖИВОТНОЕ ↔ ПЕРСОНАЖ отсутствует.',
 '- ТЁМНЫЕ и СОЛНЕЧНЫЕ ОЧКИ не слиты; обе разновидности имеют BROADER → ОЧКИ.',
 '- RELATED не является доказательством наличия объекта, темы или роли.',
 '- STYLE отмечен как absent_in_source_cards и не включён в unresolved.',
 '- 117 RK17 character bindings подтверждены; OTHER не назначен Чеддером.','',
 '## Созданные и изменённые файлы','',
 '- global_search_dictionary.v1.json — authoritative dictionary, approved.',
 '- build_search_dictionary.py — generator, читающий permanent registry.',
 '- concept_id_registry.json — permanent ID and source-binding registry.',
 '- concept_id_migration.json — rename/retype/redirect migration and changed concept_id list.',
 f'- semantic_cards.json — нормализованные {len(records)} карточки.',
 '- image_concept_bindings.json — явные image-field → concept_id bindings.',
 '- GLOBAL_SEARCH_DICTIONARY_REPORT.md — этот производный отчёт.',
 '- migrate_concept_id_registry.py — одноразовая воспроизводимая миграция legacy IDs.',
 '- migration-source/*.json — неизменяемые снимки предыдущей сборки для повторения миграции.',
 '- source-cards/*.json — исходные утверждённые карточки без художественных файлов.',
 '- validate_search_dictionary.py — независимая проверка утверждённых решений и целостности.']
(OUT/'GLOBAL_SEARCH_DICTIONARY_REPORT.md').write_text('\n'.join(report)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({'active_concepts':len(concepts),'registry_records':len(registry['concepts']),'by_type':dict(counts),'relations':dict(relcounts),'card_changes':len(card_changes),'requires_semantic_approval':remaining_approval},ensure_ascii=False,indent=2))
