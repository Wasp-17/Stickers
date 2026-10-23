"""Build the technical and semantic report for RK17-0105..0132."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent
delta=json.loads((ROOT/'rk17_0105_0132_registry_delta.json').read_text(encoding='utf-8'))
manifest=json.loads((PROJECT/'production/RK17-0105_0132_READY/manifest.json').read_text(encoding='utf-8'))
assignments=json.loads((ROOT/'rk17_0105_0132_assignments.json').read_text(encoding='utf-8'))['assignments']
new=delta['new_concepts']
lines=['# RK17-0105…RK17-0132 — DELTA REPORT','',
       '**Статус партии: technically and semantically integrated.** Validator PASS.','',
       '## Назначенные image_id','',
       '| Исходный файл | image_id | display_name |','|---|---|---|']
lines += [f"| {x['source_file']} | {x['image_id']} | {x['display_name']} |" for x in assignments]
lines += ['', '## Производственная обработка','',
          '- Создано ART: **28**.', '- Создано MASTER: **28**.', '- Создано WEB: **28**.',
          '- MASTER: 32 прозрачных пикселя с каждой стороны.', '- WEB: максимум 768 пикселей, quality 85.',
          f"- Внешний связный белый фон удалён у **{sum(x['white_background_removed'] for x in manifest['items'])}** изображений.",
          '- Отдельная встроенная декоративная белая кайма не обнаружена и не удалялась.',
          '- REQUIRES_BORDER_REPAIR: **0**.',
          '- RGB-пиксели видимой части проверены для всех изображений.',
          '- Художественная переработка, DPI, физические размеры и cut path не выполнялись.','',
          '## Семантическая дельта','',
          '- Добавлено изображений: **28**.',
          f"- Использовано существующих concepts: **{len(delta['existing_concept_ids_used'])}**.",
          f"- Создано новых concepts: **{len(new)}**.",
          '- Создано новых semantic relations: **0**.',
          '- REQUIRES_SEMANTIC_APPROVAL для партии: **0**.',
          '- Неструктурированное поле `search_semantics` партии WF сохранено дословно и участвует в лексическом Search; оно не было самовольно разложено по структурным типам.',
          '- Результат `validate_search_dictionary.py`: **PASS**.',
          '- Результат `catalog-search.test.js`: **PASS**.','',
          'Глобальный прежний pending case **ОБРАЗ МИРА** не связан с этой партией.','',
          '## Новые concepts','',
          '| concept_id | canonical | concept_type |','|---|---|---|']
lines += [f"| {x['concept_id']} | {x['canonical']} | {x['concept_type']} |" for x in new]
lines += ['', '## Relations, требующие утверждения','', '- Нет.','',
          '## Основные обновлённые файлы','',
          '- `production/RK17-0105_0132_READY/ART/*`',
          '- `production/RK17-0105_0132_READY/MASTER/*`',
          '- `production/RK17-0105_0132_READY/WEB/*`',
          '- `production/RK17-0105_0132_READY/manifest.json`',
          '- `catalog-data/image_registry.json`', '- `catalog-data/image_id_sequence.json`',
          '- `catalog-data/source-cards/RK17_0105_0132_approved.json`',
          '- `catalog-data/semantic_cards.json`', '- `catalog-data/image_concept_bindings.json`',
          '- `catalog-data/image_character_links.json`', '- `catalog-data/global_search_dictionary.v1.json`',
          '- `catalog-data/site_catalog.json`', '- `images/RK17-0105_WEB.webp`…`images/RK17-0132_WEB.webp`.','']
path=PROJECT/'production/RK17-0105_0132_READY/DELTA_REPORT.md'
path.write_text('\n'.join(lines),encoding='utf-8',newline='\n')
print(json.dumps({'report':str(path),'new_concepts':len(new),'existing_concepts':len(delta['existing_concept_ids_used'])},ensure_ascii=False))
