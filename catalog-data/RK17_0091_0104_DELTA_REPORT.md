# RK17-0091…RK17-0104 — DELTA REPORT

**Статус партии: integrated.** Семантика APPROVED, validator PASS, сайт подключён.

## Итог

- Добавлено изображений: **14** (RK17-0091…RK17-0104).
- Использовано существующих concepts: **25**.
- Создано новых concepts: **38**.
- Создано новых relations: **0**.
- REQUIRES_SEMANTIC_APPROVAL для этой партии: **0**.
- Результат `validate_search_dictionary.py`: **PASS**.

Глобальный словарь по-прежнему содержит единственный ранее зафиксированный и не связанный с этой партией pending case: **ОБРАЗ МИРА**.

## Новые concepts

| concept_id | canonical | concept_type |
|---|---|---|
| GSC-000001 | УЛЫБАТЬСЯ | ACTION |
| GSC-000002 | ХОРОШЕЕ НАСТРОЕНИЕ | INTENT |
| GSC-000003 | ХИТРОСТЬ | MOOD |
| GSC-000004 | УХМЫЛЯТЬСЯ | ACTION |
| GSC-000005 | ПРИЩУРИВАТЬСЯ | ACTION |
| GSC-000006 | ЗАДУМАЛ ЧТО-ТО | INTENT |
| GSC-000007 | УДИВЛЯТЬСЯ | ACTION |
| GSC-000008 | ПУГАТЬСЯ | ACTION |
| GSC-000009 | СКЕПСИС | MOOD |
| GSC-000010 | СОМНЕНИЕ | THEME |
| GSC-000011 | УСМЕХАТЬСЯ | ACTION |
| GSC-000012 | НЕДОВЕРИЕ | INTENT |
| GSC-000013 | СКЕПТИЧЕСКАЯ РЕАКЦИЯ | INTENT |
| GSC-000014 | РАССЛАБИТЬСЯ | INTENT |
| GSC-000015 | НЕДОВОЛЬСТВО | MOOD |
| GSC-000016 | ХМУРИТЬСЯ | ACTION |
| GSC-000017 | ЗЛИТЬСЯ | ACTION |
| GSC-000018 | СЕРДИТАЯ РЕАКЦИЯ | INTENT |
| GSC-000019 | ДРУЖЕЛЮБИЕ | THEME |
| GSC-000020 | ПРИВЕТСТВИЕ | INTENT |
| GSC-000021 | ШУТКА | INTENT |
| GSC-000022 | ОБЩЕНИЕ | THEME |
| GSC-000023 | МАХАТЬ ЛАПОЙ | ACTION |
| GSC-000024 | ПРИВЕТСТВОВАТЬ | ACTION |
| GSC-000025 | ПРИВЕТ | INTENT |
| GSC-000026 | ВСТРЕЧА | INTENT |
| GSC-000027 | ИГРА | THEME |
| GSC-000028 | ЛЕЖАТЬ НА СПИНЕ | ACTION |
| GSC-000029 | ВАЛЯТЬСЯ | ACTION |
| GSC-000030 | РАССЛАБЛЕНИЕ | INTENT |
| GSC-000031 | ДВИЖЕНИЕ | THEME |
| GSC-000032 | ПРОГУЛКА | THEME |
| GSC-000033 | ГУЛЯТЬ | ACTION |
| GSC-000034 | ИДТИ ПО ДЕЛАМ | INTENT |
| GSC-000035 | ПРОБУЖДЕНИЕ | THEME |
| GSC-000036 | ПОТЯГИВАТЬСЯ | ACTION |
| GSC-000037 | РАЗМЯТЬСЯ | INTENT |
| GSC-000038 | ПРОСНУТЬСЯ | INTENT |

## Relations, требующие утверждения

- Нет.

## Проверка файлов изображений

- Все 14 WEB-файлов сверены с `web_sha256` исходного manifest.
- В публичную папку `images` добавлены только `RK17-0091_WEB.webp`…`RK17-0104_WEB.webp`.
- ART, MASTER и производственные исходники не изменялись и в публичную папку не копировались.

## Изменённые и созданные файлы

- `images/RK17-0091_WEB.webp`…`images/RK17-0104_WEB.webp`
- `catalog-data/source-cards/RK17_0091_0104_approved.json`
- `catalog-data/concept_id_registry.json`
- `catalog-data/rk17_0091_0104_registry_delta.json`
- `catalog-data/semantic_cards.json`
- `catalog-data/image_concept_bindings.json`
- `catalog-data/image_character_links.json`
- `catalog-data/global_search_dictionary.v1.json`
- `catalog-data/site_catalog.json`
- `catalog-data/rk17_web_asset_import.json`
- `catalog-data/GLOBAL_SEARCH_DICTIONARY_REPORT.md`
- генераторы, validator и тест каталога, перечисленные в Git diff.
