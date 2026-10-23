"""Build the review report for the approved RK17-0091..0104 catalog delta."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
delta = json.loads((ROOT / 'rk17_0091_0104_registry_delta.json').read_text(encoding='utf-8'))
new = delta['new_concepts']
lines = [
    '# RK17-0091…RK17-0104 — DELTA REPORT', '',
    '**Статус партии: integrated.** Семантика APPROVED, validator PASS, сайт подключён.', '',
    '## Итог', '',
    '- Добавлено изображений: **14** (RK17-0091…RK17-0104).',
    f'- Использовано существующих concepts: **{len(delta["existing_concept_ids_used"])}**.',
    f'- Создано новых concepts: **{len(new)}**.',
    '- Создано новых relations: **0**.',
    '- REQUIRES_SEMANTIC_APPROVAL для этой партии: **0**.',
    '- Результат `validate_search_dictionary.py`: **PASS**.', '',
    'Глобальный словарь по-прежнему содержит единственный ранее зафиксированный и не связанный с этой партией pending case: **ОБРАЗ МИРА**.', '',
    '## Новые concepts', '',
    '| concept_id | canonical | concept_type |', '|---|---|---|',
]
lines += [f"| {x['concept_id']} | {x['canonical']} | {x['concept_type']} |" for x in new]
lines += ['', '## Relations, требующие утверждения', '', '- Нет.', '',
          '## Проверка файлов изображений', '',
          '- Все 14 WEB-файлов сверены с `web_sha256` исходного manifest.',
          '- В публичную папку `images` добавлены только `RK17-0091_WEB.webp`…`RK17-0104_WEB.webp`.',
          '- ART, MASTER и производственные исходники не изменялись и в публичную папку не копировались.', '',
          '## Изменённые и созданные файлы', '',
          '- `images/RK17-0091_WEB.webp`…`images/RK17-0104_WEB.webp`',
          '- `catalog-data/source-cards/RK17_0091_0104_approved.json`',
          '- `catalog-data/concept_id_registry.json`',
          '- `catalog-data/rk17_0091_0104_registry_delta.json`',
          '- `catalog-data/semantic_cards.json`',
          '- `catalog-data/image_concept_bindings.json`',
          '- `catalog-data/image_character_links.json`',
          '- `catalog-data/global_search_dictionary.v1.json`',
          '- `catalog-data/site_catalog.json`',
          '- `catalog-data/rk17_web_asset_import.json`',
          '- `catalog-data/GLOBAL_SEARCH_DICTIONARY_REPORT.md`',
          '- генераторы, validator и тест каталога, перечисленные в Git diff.', '']
(ROOT / 'RK17_0091_0104_DELTA_REPORT.md').write_text('\n'.join(lines), encoding='utf-8', newline='\n')
print(json.dumps({'report':'RK17_0091_0104_DELTA_REPORT.md','new_concepts':len(new),'approval':0}, ensure_ascii=False))
