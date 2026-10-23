# Global Search Dictionary v1.0 — migration and integrity report

**Статус: approved. ОБРАЗ МИРА остаётся единственным pending semantic case. Сайт подключён через производный site_catalog.json.**

Прочитаны 132 карточки. Активных concepts: 857. Связей: 89. Постоянных записей ID registry: 858.

## Исправления этого ревью

- Утверждённые решения перенесены в карточки, registry, bindings и граф.
- Единственный оставшийся REQUIRES_SEMANTIC_APPROVAL — ОБРАЗ МИРА.
- concept_id выдаёт только постоянный registry; rename и retype сохраняют ID.
- Source bindings разрешают одинаковое написание в разные concepts и один concept из разных полей.
- РАЗРАБОТЧИК ↔ ПРОГРАММИСТ записан как условный SYNONYM со scope software_developer.
- ИГРАЮ В ФУТБОЛ разрешается в ACTION ИГРАТЬ В ФУТБОЛ без второго морфологического concept.
- Правило OBJECT/CLOTHING применено к шляпам и очкам.
- Hard constraints записаны машинно-читаемо в rules.hard_constraints.

## Stable concept_id

- Префикс concept_id — историческая часть неизменяемого ID и не определяет текущий concept_type.
- Источник истины о типе — только поле concept_type.
- Импорт, фильтрация и Search не должны выводить тип из префикса concept_id.
- Поэтому ID вида OBJECT_… после утверждённого retype может иметь concept_type CLOTHING.

## Воспроизводимость

- Повторная сборка гарантирует идентичную JSON-структуру и данные при одинаковых исходных файлах и версии генератора.
- Для генерируемых JSON и Markdown также зафиксированы UTF-8 без BOM, LF, лексикографический порядок ключей JSON, детерминированный порядок массивов, отступ 2 пробела и финальный LF.
- Побайтовая идентичность контейнера ZIP не заявляется: метаданные архива могут зависеть от упаковщика.

## Количество concepts по типам

| Тип | Количество |
|---|---:|
| SUBJECT | 6 |
| ROLE | 52 |
| MOOD | 71 |
| THEME | 183 |
| ACTION | 149 |
| OBJECT | 116 |
| SCENARIO_CONCEPT | 8 |
| INTENT | 208 |
| CLOTHING | 60 |
| DECORATION | 4 |
| STYLE | 0 |

## Количество связей

| Связь | Количество |
|---|---:|
| SYNONYM | 6 |
| COLLOQUIAL | 2 |
| BROADER | 16 |
| NARROWER | 16 |
| RELATED | 49 |

## Изменённые concept_id

- OBJECT_E088CF6E529952F2: canonical АРТЕФАКТ/ОСТАНКИ → ДРЕВНЯЯ НАХОДКА; ID сохранён.
- CLOTHING_63A0098198B110D5: canonical БАБОЧКА → ГАЛСТУК-БАБОЧКА; ID сохранён.
- OBJECT_1F51D90E60F35336: canonical КОНЬ → ШАХМАТНЫЙ КОНЬ; ID сохранён.
- THEME_16827D589E6F04AB: canonical МИР → ОКРУЖАЮЩИЙ МИР; ID сохранён.
- OBJECT_69682F813D2ADA8E: canonical КИСТЬ → КИСТЬ (ИНСТРУМЕНТ); ID сохранён.
- OBJECT_3391CAD0210C9B60: concept_type OBJECT → CLOTHING; ID сохранён.
- OBJECT_56E61B4223D3DB06: concept_type OBJECT → CLOTHING; ID сохранён.
- OBJECT_EE381614F191A450: concept_type OBJECT → CLOTHING; ID сохранён.
- OBJECT_FCC46A4280BBF672: concept_type OBJECT → CLOTHING; ID сохранён.
- INTENT_5836FBC9A0DA8468: retired redirect → ACTION_729E1802333D3582.

## Изменения semantic cards

- RK17-0001: role; АСТРОНАВТ → КОСМОНАВТ (ROLE_COSMONAUT).
- RK17-0002: role; АСТРОНАВТ → КОСМОНАВТ (ROLE_COSMONAUT).
- RK17-0003: role; АСТРОНАВТ → КОСМОНАВТ (ROLE_COSMONAUT).
- RK17-0022: objects; кисть → КИСТЬ (ИНСТРУМЕНТ) (OBJECT_69682F813D2ADA8E).
- RK17-0029: themes; мир → ОКРУЖАЮЩИЙ МИР (THEME_16827D589E6F04AB).
- RK17-0032: objects; кисточка → КИСТЬ (ИНСТРУМЕНТ) (OBJECT_69682F813D2ADA8E).
- RK17-0039: clothing; бабочка → ГАЛСТУК-БАБОЧКА (CLOTHING_63A0098198B110D5).
- RK17-0041: objects → clothing; шляпа → шляпа (OBJECT_FCC46A4280BBF672).
- RK17-0042: objects → clothing; шляпа → шляпа (OBJECT_FCC46A4280BBF672).
- RK17-0056: clothing; бабочка → ГАЛСТУК-БАБОЧКА (CLOTHING_63A0098198B110D5).
- RK17-0065: objects; конь → ШАХМАТНЫЙ КОНЬ (OBJECT_1F51D90E60F35336).
- RK17-0074: objects → clothing; тёмные очки → тёмные очки (OBJECT_56E61B4223D3DB06).
- RK17-0075: objects → clothing; тёмные очки → тёмные очки (OBJECT_56E61B4223D3DB06).
- OTHER-0076: objects → clothing; очки → очки (OBJECT_3391CAD0210C9B60).
- OTHER-0078: objects; кисть → КИСТЬ (ИНСТРУМЕНТ) (OBJECT_69682F813D2ADA8E).
- OTHER-0078: objects; артефакт/останки → ДРЕВНЯЯ НАХОДКА (OBJECT_E088CF6E529952F2).
- OTHER-0081: role; АСТРОНАВТ, КОСМОНАВТ → КОСМОНАВТ (ROLE_COSMONAUT).
- OTHER-0084: objects → clothing; тёмные очки → тёмные очки (OBJECT_56E61B4223D3DB06).
- OTHER-0086: objects → clothing; солнечные очки → солнечные очки (OBJECT_EE381614F191A450).

## Все канонические concepts

| concept_id | canonical | concept_type | Статус |
|---|---|---|---|
| ACTION_D414574A2AACD6BE | АНАЛИЗИРОВАТЬ | ACTION | approved |
| ACTION_337FC9C58F049EEE | БЕЖАТЬ | ACTION | approved |
| GSC-000029 | ВАЛЯТЬСЯ | ACTION | approved |
| GSC-000067 | ВЕСТИ ГРУЗОВИК | ACTION | approved |
| ACTION_71EE958F662665FA | ВЕСТИ ПЕРЕГОВОРЫ | ACTION | approved |
| ACTION_CAAD3CBFDF65B90B | ВОЗМУЩАТЬСЯ | ACTION | approved |
| ACTION_E5BD33CC8E9EE7F1 | ВЫГНУТЬ СПИНУ | ACTION | approved |
| ACTION_4E11A2A58540B65E | ВЫСТУПАТЬ | ACTION | approved |
| ACTION_61BD77601A25C0E1 | ГОТОВИТЬ | ACTION | approved |
| GSC-000077 | ГОТОВИТЬСЯ К РЕЙСУ | ACTION | approved |
| GSC-000033 | ГУЛЯТЬ | ACTION | approved |
| ACTION_01E8D931E4834231 | ДАРИТЬ ЦВЕТЫ | ACTION | approved |
| ACTION_CFB63C6812E05712 | ДЕГУСТИРОВАТЬ | ACTION | approved |
| GSC-000128 | ДЕЛАТЬ ЗАПИСЬ | ACTION | approved |
| ACTION_B6B079414ED620BD | ДЕЛАТЬ НАБРОСКИ | ACTION | approved |
| ACTION_FDC33D7DD7D90CF6 | ДЕЛАТЬ ПАУЗУ | ACTION | approved |
| ACTION_B2895D6A602AD5DA | ДЕЛАТЬ ХОД | ACTION | approved |
| ACTION_7745D0A090497877 | ДЕМОНСТРИРОВАТЬ КАРТЫ | ACTION | approved |
| ACTION_70FC4FAC88F7E4B6 | ДЕМОНСТРИРОВАТЬ СТАТУС | ACTION | approved |
| ACTION_EC3F61325E906446 | ДЕМОНСТРИРОВАТЬ ТАТУИРОВКУ | ACTION | approved |
| GSC-000104 | ДЕРЖАТЬ АПТЕЧКУ | ACTION | approved |
| GSC-000044 | ДЕРЖАТЬ ДИПЛОМ | ACTION | approved |
| GSC-000116 | ДЕРЖАТЬ КОЛБУ | ACTION | approved |
| ACTION_3A0CA8BE37A42D6B | ДЕРЖАТЬ КОФЕ | ACTION | approved |
| ACTION_3085924199C1F9A9 | ДЕРЖАТЬ КРУЖКУ | ACTION | approved |
| GSC-000088 | ДЕРЖАТЬ ПЛАНШЕТ | ACTION | approved |
| ACTION_C6CDD25A9A7E2145 | ДЕРЖАТЬ РИТМ | ACTION | approved |
| GSC-000068 | ДЕРЖАТЬ РУЛЬ | ACTION | approved |
| ACTION_6BF0486D94A7F929 | ДЕРЖАТЬСЯ ЗА РЕШЁТКУ | ACTION | approved |
| ACTION_D169DF5828C5D7BB | ДРОЖАТЬ | ACTION | approved |
| ACTION_5DA81144D63682EF | ЗАПУСКАТЬ | ACTION | approved |
| GSC-000017 | ЗЛИТЬСЯ | ACTION | approved |
| ACTION_4BF097C90DBD6412 | ИГРАТЬ | ACTION | approved |
| ACTION_729E1802333D3582 | ИГРАТЬ В ФУТБОЛ | ACTION | approved |
| ACTION_56DE519E795C8F1E | ИГРАТЬ В ШАХМАТЫ | ACTION | approved |
| ACTION_B85FBAAB9F30296D | ИГРАТЬ МУЗЫКУ | ACTION | approved |
| ACTION_9880F6C328DF86F7 | ИГРАТЬ НА ГИТАРЕ | ACTION | approved |
| ACTION_CC68047838CDCF8B | ИДТИ | ACTION | approved |
| ACTION_BCF7C55673C70EC6 | ИДТИ В ПОХОД | ACTION | approved |
| ACTION_A74A1AE3A1F92F3F | ИДТИ ПО СНЕГУ | ACTION | approved |
| ACTION_095F9CAEA67430CB | ИЗУЧАТЬ | ACTION | approved |
| ACTION_A0C3BB21A0261EE5 | ИЗУЧАТЬ КАРТУ | ACTION | approved |
| ACTION_462D446C391D4E5B | ИЗУЧАТЬ СЛЕДЫ | ACTION | approved |
| GSC-000095 | ИЗУЧАТЬ СНИМОК | ACTION | approved |
| ACTION_D48D85B09EE1E7FC | ИЗУЧАТЬ УЛИКУ | ACTION | approved |
| ACTION_3401C377D47D9164 | ИЗУЧАТЬ ЧЕРТЁЖ | ACTION | approved |
| ACTION_8E38259E2E678869 | ИСКАТЬ | ACTION | approved |
| ACTION_E62C488E321159BE | ИСКАТЬ ДОРОГУ | ACTION | approved |
| ACTION_3741249E8F6A55D0 | ИСКАТЬ ИСТИНУ | ACTION | approved |
| ACTION_8CE59387A033F235 | ИСКАТЬ МЕСТО | ACTION | approved |
| ACTION_6E6D150197D74DC5 | ИСКАТЬ ПРИКЛЮЧЕНИЯ | ACTION | approved |
| ACTION_324D51133D0342A8 | ИСПУГАТЬСЯ | ACTION | approved |
| ACTION_E5AAF2BC1E9ABC95 | ИСПЫТЫВАТЬ | ACTION | approved |
| ACTION_ED5DFE8F788DDF33 | ИССЛЕДОВАТЬ | ACTION | approved |
| ACTION_4D042D5C08A99055 | ЛЕЖАТЬ В ГАМАКЕ | ACTION | approved |
| GSC-000028 | ЛЕЖАТЬ НА СПИНЕ | ACTION | approved |
| ACTION_66B73062CBD32514 | ЛЕТЕТЬ | ACTION | approved |
| GSC-000112 | ЛЕЧИТЬ | ACTION | approved |
| ACTION_F076016FEF0DF63A | ЛОВИТЬ ЛИСТЬЯ | ACTION | approved |
| ACTION_562B439E82E2C167 | МЁРЗНУТЬ | ACTION | approved |
| GSC-000023 | МАХАТЬ ЛАПОЙ | ACTION | approved |
| ACTION_970C3E1605ED1B16 | МАХАТЬ НА ПРОЩАНИЕ | ACTION | approved |
| ACTION_9838558FD0281DCF | МЕЧТАТЬ | ACTION | approved |
| ACTION_F0F015B6F92FA531 | НАБЛЮДАТЬ | ACTION | approved |
| ACTION_BAD4AFC5F292C207 | НАЙТИ | ACTION | approved |
| ACTION_844BE506E83230D7 | НАРЕЗАТЬ | ACTION | approved |
| ACTION_B9C38FBA5EC98199 | НАСЛАЖДАТЬСЯ | ACTION | approved |
| ACTION_E7535E5858D54414 | ОБНАРУЖИВАТЬ | ACTION | approved |
| ACTION_997893EC6B85A3CF | ОБСУЖДАТЬ ДЕЛА | ACTION | approved |
| ACTION_51EAB262CDDD6DFB | ОБЪЯСНЯТЬ | ACTION | approved |
| GSC-000057 | ОПИРАТЬСЯ НА ГРУЗОВИК | ACTION | approved |
| ACTION_8AE969EC4FA2D099 | ОРИЕНТИРОВАТЬСЯ ПО КАРТЕ | ACTION | approved |
| GSC-000111 | ОСМАТРИВАТЬ ЩЕНКА | ACTION | approved |
| ACTION_6FEA812E6AD218E4 | ОТБЫВАТЬ СРОК | ACTION | approved |
| ACTION_093D746ECD486ADE | ОТДЫХАТЬ | ACTION | approved |
| ACTION_8876B7C69D642752 | ОТМЕЧАТЬ ЗАДАЧИ | ACTION | approved |
| ACTION_D78F04640AE726D3 | ОТПРАВЛЯТЬСЯ В ПУТЬ | ACTION | approved |
| ACTION_12E1804767858F21 | ПАРИТЬ | ACTION | approved |
| ACTION_CA8AFB5FA6F09809 | ПЕТЬ | ACTION | approved |
| ACTION_68700DBDD81458CD | ПИТЬ ГОРЯЧИЙ НАПИТОК | ACTION | approved |
| ACTION_A52C0AA80630EBE5 | ПИТЬ ИЗ КРУЖКИ | ACTION | approved |
| ACTION_584E3A41E3E9A91B | ПЛАНИРОВАТЬ | ACTION | approved |
| GSC-000076 | ПЛАНИРОВАТЬ МАРШРУТ | ACTION | approved |
| ACTION_4B7417C6D3C3CDD5 | ПЛАНИРОВАТЬ СТРАТЕГИЮ | ACTION | approved |
| ACTION_1C4468C7E8C9DD34 | ПОДАВАТЬ БЛЮДО | ACTION | approved |
| ACTION_4E88D2A1FC423C72 | ПОДМИГИВАТЬ | ACTION | approved |
| ACTION_D8485C825E1015E1 | ПОДНИМАТЬ ВЕС | ACTION | approved |
| ACTION_87A755FF69DC3A82 | ПОДНИМАТЬ ГАНТЕЛЬ | ACTION | approved |
| ACTION_60BD3821D30A7F2E | ПОДСКОЧИТЬ | ACTION | approved |
| ACTION_FB02BEA1341AD69E | ПОЗИРОВАТЬ | ACTION | approved |
| ACTION_0FCF9407B9F5CBDA | ПОКАЗЫВАТЬ ФОКУС | ACTION | approved |
| ACTION_4FA660809B09FEED | ПОМЕШИВАТЬ | ACTION | approved |
| GSC-000036 | ПОТЯГИВАТЬСЯ | ACTION | approved |
| GSC-000050 | ПРАЗДНОВАТЬ | ACTION | approved |
| ACTION_8A5636C6EFBA3FD9 | ПРЕЗЕНТОВАТЬ | ACTION | approved |
| GSC-000024 | ПРИВЕТСТВОВАТЬ | ACTION | approved |
| ACTION_D750319E335C17A6 | ПРИДУМЫВАТЬ | ACTION | approved |
| ACTION_9674B466D6BEAF5E | ПРИНИМАТЬ РЕШЕНИЕ | ACTION | approved |
| GSC-000005 | ПРИЩУРИВАТЬСЯ | ACTION | approved |
| ACTION_F199164F4FEB18B8 | ПРОБОВАТЬ | ACTION | approved |
| GSC-000117 | ПРОВОДИТЬ ОПЫТ | ACTION | approved |
| ACTION_EA9A0E3456224CC3 | ПРОГРАММИРОВАТЬ | ACTION | approved |
| ACTION_77DA6CD0C102BEA4 | ПРОЕКТИРОВАТЬ | ACTION | approved |
| ACTION_522F4C072D769425 | ПРОЛИТЬ | ACTION | approved |
| GSC-000008 | ПУГАТЬСЯ | ACTION | approved |
| ACTION_EF85C385090A68AC | ПУТЕШЕСТВОВАТЬ | ACTION | approved |
| ACTION_AB389B6BF3BC468A | РАБОТАТЬ | ACTION | approved |
| ACTION_D614EC277E919BED | РАБОТАТЬ ЗА КОМПЬЮТЕРОМ | ACTION | approved |
| ACTION_01871D6DC603B302 | РАБОТАТЬ ЗА НОУТБУКОМ | ACTION | approved |
| ACTION_AB04A44D05C5A267 | РАДОВАТЬСЯ | ACTION | approved |
| ACTION_E978482CFC361C1C | РАЗГОВАРИВАТЬ ПО ТЕЛЕФОНУ | ACTION | approved |
| ACTION_78340EB8526D45FE | РАЗДЕЛЫВАТЬ РЫБУ | ACTION | approved |
| ACTION_7C1BF90556397F52 | РАЗМЫШЛЯТЬ | ACTION | approved |
| ACTION_2C7AE4F9D0981DEA | РАСКАПЫВАТЬ | ACTION | approved |
| ACTION_B4A30351A2EDA745 | РАССЛЕДОВАТЬ | ACTION | approved |
| ACTION_2B901D434D531D59 | РАСЧИЩАТЬ | ACTION | approved |
| ACTION_E19BEF70B4C3C549 | РАСЧИЩАТЬ НАХОДКУ | ACTION | approved |
| ACTION_38FE7EBFBEB1C197 | РЕМОНТИРОВАТЬ | ACTION | approved |
| ACTION_157FCB523396F345 | РИСОВАТЬ | ACTION | approved |
| ACTION_D4CF7BFE2F9440C1 | РУКОВОДИТЬ | ACTION | approved |
| ACTION_1A354655ABFCE90C | СЕРДИТЬСЯ | ACTION | approved |
| ACTION_0B9E8A0192FD0166 | СИДЕТЬ | ACTION | approved |
| ACTION_2C38DBC075D9D473 | СИДЕТЬ НА ТРОНЕ | ACTION | approved |
| ACTION_D48760255785440A | СЛУШАТЬ МУЗЫКУ | ACTION | approved |
| ACTION_83A72FB65BEC6B4A | СМОТРЕТЬ В КОСМОС | ACTION | approved |
| GSC-000122 | СМОТРЕТЬ В МИКРОСКОП | ACTION | approved |
| ACTION_ED444080EEFC3988 | СМОТРЕТЬ В ОКНО | ACTION | approved |
| ACTION_8C43D2006C4C34BE | СМОТРЕТЬ НА ЗВЁЗДЫ | ACTION | approved |
| ACTION_82E9AEAD8D0F97D9 | СМОТРЕТЬ НА ЗЕМЛЮ | ACTION | approved |
| ACTION_01B5BE0FB25E25D2 | СМОТРЕТЬ НА ПЕЙЗАЖ | ACTION | approved |
| ACTION_A9951C50557DE026 | СОБИРАТЬ | ACTION | approved |
| ACTION_9316736FB9A1DA6A | СОЗЕРЦАТЬ | ACTION | approved |
| ACTION_F6FBF47BADD5D71A | СОСТАВЛЯТЬ СПИСОК | ACTION | approved |
| ACTION_E120A3195C4272ED | СПАТЬ | ACTION | approved |
| ACTION_902F5216044BF9A5 | СТАВИТЬ ЦЕЛИ | ACTION | approved |
| GSC-000080 | СТОЯТЬ РЯДОМ С ГРУЗОВИКОМ | ACTION | approved |
| ACTION_10305AE4C836D2D3 | ТВОРИТЬ | ACTION | approved |
| ACTION_D64F2EAE98664FDB | ТРЕНИРОВАТЬСЯ | ACTION | approved |
| GSC-000007 | УДИВЛЯТЬСЯ | ACTION | approved |
| GSC-000129 | УКАЗЫВАТЬ ВВЕРХ | ACTION | approved |
| GSC-000001 | УЛЫБАТЬСЯ | ACTION | approved |
| GSC-000011 | УСМЕХАТЬСЯ | ACTION | approved |
| GSC-000004 | УХМЫЛЯТЬСЯ | ACTION | approved |
| ACTION_AAF0F96928E7E308 | УЧИТЬСЯ | ACTION | approved |
| ACTION_97B6418656F99F6B | ФЕХТОВАТЬ | ACTION | approved |
| ACTION_28E409ADEBC4CC22 | ФОТОГРАФИРОВАТЬ | ACTION | approved |
| GSC-000016 | ХМУРИТЬСЯ | ACTION | approved |
| ACTION_39F6FBBACD6E0E74 | ЧИТАТЬ | ACTION | approved |
| ACTION_0014EFFEAA578255 | ЭКСПЕРИМЕНТИРОВАТЬ | ACTION | approved |
| GSC-000046 | АКАДЕМИЧЕСКАЯ МАНТИЯ | CLOTHING | approved |
| CLOTHING_A483E166376E73D9 | БЕЛАЯ РУБАШКА | CLOTHING | approved |
| GSC-000090 | БЕЛЫЙ ХАЛАТ | CLOTHING | approved |
| GSC-000062 | БОТИНКИ | CLOTHING | approved |
| CLOTHING_B0171AF1E5C322C9 | ВАЛЕНКИ | CLOTHING | approved |
| CLOTHING_91035E1F797D49B7 | ГАЛСТУК | CLOTHING | approved |
| CLOTHING_63A0098198B110D5 | ГАЛСТУК-БАБОЧКА | CLOTHING | approved |
| CLOTHING_669EBE193393D505 | ДЕЛОВОЙ КОСТЮМ | CLOTHING | approved |
| CLOTHING_5BD047FC18C45DDF | ДЕТЕКТИВНАЯ КЕПКА | CLOTHING | approved |
| CLOTHING_70175A8F874B7AE5 | ДЕТЕКТИВНЫЙ КОСТЮМ | CLOTHING | approved |
| CLOTHING_EF596ABFE4035BEA | ДЕТЕКТИВНЫЙ ОБРАЗ | CLOTHING | approved |
| GSC-000061 | ДЖИНСЫ | CLOTHING | approved |
| CLOTHING_0E624A802B19243F | ЖИЛЕТ | CLOTHING | approved |
| CLOTHING_C769F0F401CE3F1F | ЗАНОШЕННАЯ БЕЛАЯ МАЙКА | CLOTHING | approved |
| CLOTHING_59E7960765C53B41 | ЗАЩИТНЫЕ ОЧКИ | CLOTHING | approved |
| CLOTHING_BE3D96041144BE49 | ЗИМНЯЯ ОДЕЖДА | CLOTHING | approved |
| CLOTHING_E51CE8739C4469C5 | ИМПЕРАТОРСКИЙ НАРЯД | CLOTHING | approved |
| CLOTHING_397202441A348B4A | КЕПКА | CLOTHING | approved |
| GSC-000071 | КЛЕТЧАТАЯ РУБАШКА | CLOTHING | approved |
| CLOTHING_DC01903CE66A673C | КОРОЛЕВСКАЯ МАНТИЯ | CLOTHING | approved |
| CLOTHING_FC13003D8CDFD33C | КОРОЛЕВСКИЙ НАРЯД | CLOTHING | approved |
| CLOTHING_25FD0A0FCF2C2FFE | КОРОНА | CLOTHING | approved |
| CLOTHING_B3D21E9220987838 | КОСТЮМ МУШКЕТЁРА | CLOTHING | approved |
| CLOTHING_A029C9966E535EC1 | КРАСНЫЙ ХУДИ | CLOTHING | approved |
| GSC-000060 | КУРТКА | CLOTHING | approved |
| CLOTHING_F5EFCD7B785CA3E9 | ЛАБОРАТОРНАЯ ОДЕЖДА | CLOTHING | approved |
| GSC-000120 | ЛАБОРАТОРНЫЙ ХАЛАТ | CLOTHING | approved |
| GSC-000097 | МЕДИЦИНСКАЯ ФОРМА | CLOTHING | approved |
| CLOTHING_65204913E0CF7BA8 | ОДЕЖДА АРХЕОЛОГА | CLOTHING | approved |
| GSC-000082 | ОДЕЖДА ВОДИТЕЛЯ | CLOTHING | approved |
| OBJECT_3391CAD0210C9B60 | ОЧКИ | CLOTHING | approved |
| GSC-000130 | ОЧКИ НА ГОЛОВЕ | CLOTHING | approved |
| CLOTHING_F71DBF13FC2570AB | ПЕРЧАТКИ | CLOTHING | approved |
| CLOTHING_ED516D0279358FE9 | ПЛАЩ | CLOTHING | approved |
| CLOTHING_97AF954FFA415F5F | ПОВАРСКАЯ ОДЕЖДА | CLOTHING | approved |
| CLOTHING_EE9E7CA60AAE11DD | ПОВАРСКОЙ КОЛПАК | CLOTHING | approved |
| CLOTHING_FB51CA857D0D4531 | ПОЛЕВАЯ ШЛЯПА | CLOTHING | approved |
| CLOTHING_76BA6668712C6D33 | ПОЛОСАТАЯ ТЮРЕМНАЯ ОДЕЖДА | CLOTHING | approved |
| CLOTHING_3F5DB2675CD3B9C6 | ПРИКЛЮЧЕНЧЕСКИЙ КОСТЮМ | CLOTHING | approved |
| GSC-000078 | РАБОЧАЯ ОДЕЖДА | CLOTHING | approved |
| CLOTHING_5D2563387E28545D | РУБАШКА | CLOTHING | approved |
| CLOTHING_530A7A3014321476 | СКАФАНДР | CLOTHING | approved |
| OBJECT_EE381614F191A450 | СОЛНЕЧНЫЕ ОЧКИ | CLOTHING | approved |
| CLOTHING_DDD1CC0D0984BBF4 | СПОРТИВНАЯ ОДЕЖДА | CLOTHING | approved |
| CLOTHING_4EF126733A677997 | СПОРТИВНАЯ ПОВЯЗКА | CLOTHING | approved |
| CLOTHING_5CB9197B5AC8DC73 | СЦЕНИЧЕСКИЙ ЖИЛЕТ | CLOTHING | approved |
| CLOTHING_0CCBE18D2CC804F4 | СЦЕНИЧЕСКИЙ КОСТЮМ | CLOTHING | approved |
| OBJECT_56E61B4223D3DB06 | ТЁМНЫЕ ОЧКИ | CLOTHING | approved |
| CLOTHING_DC1E1D6F40EF7C0A | ТУРИСТИЧЕСКАЯ ОДЕЖДА | CLOTHING | approved |
| CLOTHING_887D1D72987C8E07 | ТЮРЕМНАЯ ШАПКА | CLOTHING | approved |
| CLOTHING_3269844771F2DB44 | УКРАШЕНИЯ | CLOTHING | approved |
| CLOTHING_8F42D707E05C7C3D | УШАНКА | CLOTHING | approved |
| CLOTHING_B905DBF30D5B75F8 | ФАРТУК | CLOTHING | approved |
| CLOTHING_747F674D787DAF28 | ФУТБОЛКА «БЕГУ К ЛУЧШЕЙ ВЕРСИИ СЕБЯ» | CLOTHING | approved |
| GSC-000098 | ХАЛАТ | CLOTHING | approved |
| CLOTHING_778E8DFBA68063ED | ЦИЛИНДР | CLOTHING | approved |
| CLOTHING_C90F8D60FFCE51B3 | ЧЁРНЫЙ ДЕЛОВОЙ КОСТЮМ | CLOTHING | approved |
| GSC-000099 | ШАПОЧКА | CLOTHING | approved |
| CLOTHING_A2C738DD2C33A77E | ШАРФ | CLOTHING | approved |
| OBJECT_FCC46A4280BBF672 | ШЛЯПА | CLOTHING | approved |
| DECORATION_BEABE88773AE0140 | ДРАГОЦЕННЫЕ КАМНИ | DECORATION | approved |
| DECORATION_EBD9C8C295085ECE | ЗОЛОТО | DECORATION | approved |
| DECORATION_27F67DED9CB2C015 | МУЗЫКАЛЬНЫЕ НОТЫ | DECORATION | approved |
| DECORATION_802379BF5EA9D9AC | ТАТУИРОВКА | DECORATION | approved |
| INTENT_BE972DB20A7FA237 | АВТОРИТЕТ | INTENT | approved |
| INTENT_2A5B042E6BEC924C | АКТИВНОСТЬ | INTENT | approved |
| INTENT_B39227BCDB30F993 | АКТИВНЫЙ ОТДЫХ | INTENT | approved |
| GSC-000101 | АНАЛИЗ | INTENT | approved |
| INTENT_4F747F0F0B4F29F9 | АППЕТИТ | INTENT | approved |
| INTENT_B473084391794214 | БЕСИТ | INTENT | approved |
| INTENT_DC4EEB996DE3102E | БОГАТАЯ ЖИЗНЬ | INTENT | approved |
| INTENT_3AFC157A3A1D3466 | БОЛЬШИЕ ДЕНЬГИ | INTENT | approved |
| INTENT_FFDDA2916F05E236 | В ПРОЦЕССЕ | INTENT | approved |
| INTENT_6758422DF49BD7B4 | ВАЖНОСТЬ | INTENT | approved |
| INTENT_6AF1C08CFB902D0B | ВАЖНЫЕ ПЕРЕГОВОРЫ | INTENT | approved |
| INTENT_2326E13EC5DC80C2 | ВАЖНЫЙ ЗВОНОК | INTENT | approved |
| INTENT_A3F8FAD6A3655739 | ВЕСЕЛЬЕ | INTENT | approved |
| INTENT_7BC4D403528E7B59 | ВКУСНАЯ ЕДА | INTENT | approved |
| INTENT_30CC67CC285F58B3 | ВНЕЗАПНАЯ РЕАКЦИЯ | INTENT | approved |
| INTENT_FB8B1B442F96FDA3 | ВСЁ ВПЕРЕДИ | INTENT | approved |
| INTENT_EFA8B5927C024A22 | ВСЁ КРУТО | INTENT | approved |
| INTENT_0F4D6B51A1DF2533 | ВСЁ ПО ПЛАНУ | INTENT | approved |
| INTENT_010CFEAFB99338E8 | ВСЁ ХОРОШО | INTENT | approved |
| GSC-000026 | ВСТРЕЧА | INTENT | approved |
| INTENT_9A2BB1729F037603 | ВЫРАЗИТЬ СИМПАТИЮ | INTENT | approved |
| INTENT_242F5E4E696ECAD5 | ГЕРОЙСКИЙ ОБРАЗ | INTENT | approved |
| INTENT_39AE6FE2231D146E | ГОТОВ К РАБОТЕ | INTENT | approved |
| INTENT_8F26AC4ED4CE9FF6 | ГОТОВИТЬ ЕДУ | INTENT | approved |
| INTENT_2322C92F637F85B8 | ГОТОВКА | INTENT | approved |
| INTENT_42602BE3FD92FFB0 | ДЕЛАЮ ЭСКИЗ | INTENT | approved |
| INTENT_BFFAD14EB2C4A459 | ДЕЛОВОЙ ЗВОНОК | INTENT | approved |
| INTENT_2986C76443847BA6 | ДЕЛОВОЙ РАЗГОВОР | INTENT | approved |
| INTENT_2B2C36AAE1742AE9 | ДЕМОНСТРАЦИЯ СТАТУСА | INTENT | approved |
| INTENT_6873AB85FD751F65 | ДЛЯ ТЕБЯ | INTENT | approved |
| INTENT_405C39A4604D38A4 | ДОБРОЕ УТРО | INTENT | approved |
| INTENT_8EA8A98E63D0C635 | ДОВОЛЕН ЖИЗНЬЮ | INTENT | approved |
| INTENT_E22B97443B1ECCF3 | ДОКОПАТЬСЯ ДО ИСТИНЫ | INTENT | approved |
| INTENT_30B70C68652AEA23 | ДОМАШНИЙ ВЕЧЕР | INTENT | approved |
| GSC-000048 | ДОСТИЖЕНИЕ | INTENT | approved |
| INTENT_D93ED95E108B40CE | ДУБАК | INTENT | approved |
| INTENT_76B584459939CE78 | ДУМАЮ НАД ПЛАНОМ | INTENT | approved |
| INTENT_4A0563A1A3BA27DA | ЕСТЬ РИТМ | INTENT | approved |
| INTENT_907EF68EFF8A2DE4 | ЖИЗНЬ УДАЛАСЬ | INTENT | approved |
| INTENT_772E23F4E8C3EDD5 | ЗА РЕШЁТКОЙ | INTENT | approved |
| GSC-000072 | ЗА РУЛЁМ | INTENT | approved |
| INTENT_23F11402431F457E | ЗА ЧТО | INTENT | approved |
| INTENT_8F271FDD3CCF0B78 | ЗАБЛУДИЛСЯ | INTENT | approved |
| GSC-000107 | ЗАБОТА | INTENT | approved |
| GSC-000051 | ЗАВЕРШЕНИЕ УЧЁБЫ | INTENT | approved |
| GSC-000006 | ЗАДУМАЛ ЧТО-ТО | INTENT | approved |
| INTENT_AC76D003E947E365 | ЗАЖИГАЕМ | INTENT | approved |
| INTENT_1D555326375545D1 | ЗАНИМАТЬСЯ СПОРТОМ | INTENT | approved |
| INTENT_254076402BFE0CCB | ЗИМНЕЕ НАСТРОЕНИЕ | INTENT | approved |
| INTENT_BB427FEC415D0EF0 | ЗИМНЕЕ ПУТЕШЕСТВИЕ | INTENT | approved |
| INTENT_A3C725737266E20C | ЗИМНИЙ УЮТ | INTENT | approved |
| INTENT_23E464633EAC0E7D | ЗНАК ВНИМАНИЯ | INTENT | approved |
| INTENT_F67F5CCCCF560210 | ИГРА ВДВОЁМ | INTENT | approved |
| GSC-000034 | ИДТИ ПО ДЕЛАМ | INTENT | approved |
| INTENT_5D4CBCA00F3404C9 | ИЗОБИЛИЕ | INTENT | approved |
| INTENT_7A4AAD034147064C | ИЗУЧАЮ IT | INTENT | approved |
| GSC-000124 | ИЗУЧЕНИЕ | INTENT | approved |
| INTENT_E3126D5872A562DF | ИМПЕРАТОР ЖИЗНИ | INTENT | approved |
| INTENT_7C9DC84B6300E877 | ИССЛЕДОВАНИЕ | INTENT | approved |
| INTENT_752502999CC27654 | ИЩУ ДОКАЗАТЕЛЬСТВА | INTENT | approved |
| INTENT_F16A565A0E057F07 | ИЩУ ИДЕЮ | INTENT | approved |
| INTENT_544851BA2AF92405 | ИЩУ МАРШРУТ | INTENT | approved |
| INTENT_81F607352E795B0D | ИЩУ МЕСТО | INTENT | approved |
| INTENT_7B185C3F79FAC211 | КАЙФУЮ | INTENT | approved |
| INTENT_FC6D48F467266090 | КАК ОН ЭТО СДЕЛАЛ | INTENT | approved |
| INTENT_7D91C23B99DB2B42 | КАНИКУЛЫ | INTENT | approved |
| INTENT_30D13E9E5ACEEE67 | КАРТОЧНЫЙ ТРЮК | INTENT | approved |
| INTENT_3AB39789EF96F0CF | КАЧАЮСЬ | INTENT | approved |
| INTENT_4AF5E2FA498F2BE6 | КОРОЛЬ БОГАТСТВА | INTENT | approved |
| INTENT_4DCCC784DAD59CF9 | КУДА ИДТИ | INTENT | approved |
| INTENT_F7A4B7E1B651C2AE | КУЛИНАРНОЕ ТВОРЧЕСТВО | INTENT | approved |
| INTENT_C808298C1BFF301E | ЛУЧШАЯ ВЕРСИЯ СЕБЯ | INTENT | approved |
| INTENT_5DE955E87A28E0A3 | ЛЮБИМАЯ МУЗЫКА | INTENT | approved |
| INTENT_C8018872CD971484 | ЛЮБИТЕЛЬ ЧТЕНИЯ | INTENT | approved |
| INTENT_31A1E985BE911298 | ЛЮБОВАТЬСЯ ЗВЁЗДАМИ | INTENT | approved |
| INTENT_11E3B97AFE539159 | ЛЮБОВАТЬСЯ ПРИРОДОЙ | INTENT | approved |
| INTENT_988FD88429ABDF7C | ЛЮБОВЬ К ГОТОВКЕ | INTENT | approved |
| INTENT_BFECEEACCA36CEE6 | МАЛЕНЬКАЯ КАТАСТРОФА | INTENT | approved |
| GSC-000073 | МАРШРУТ | INTENT | approved |
| INTENT_B2CE910982B91CCA | МАРШРУТ К ДРЕВНОСТЯМ | INTENT | approved |
| INTENT_D37B5D3B543C8F4F | МНЕ СТРАШНО | INTENT | approved |
| INTENT_DF6A95E058EBAE4F | МОТАТЬ СРОК | INTENT | approved |
| INTENT_0615AA8D5CA7649A | НАЙТИ ЗАЦЕПКУ | INTENT | approved |
| INTENT_70107C36DE374145 | НАЙТИ РЕШЕНИЕ | INTENT | approved |
| INTENT_E7DB26DDB38CE316 | НАКИПЕЛО | INTENT | approved |
| INTENT_8DA856EBEB44F59C | НАУЧНАЯ НАХОДКА | INTENT | approved |
| INTENT_1976568707B13C24 | НАХОДКА | INTENT | approved |
| INTENT_03D5D23214768224 | НАЧАЛЬНИК | INTENT | approved |
| INTENT_088C6896A175504C | НЕ ПОЛУЧАЕТСЯ ЗАДАЧА | INTENT | approved |
| GSC-000012 | НЕДОВЕРИЕ | INTENT | approved |
| INTENT_80E1659361A43B82 | НЕМНОГО ОТДЫХА | INTENT | approved |
| INTENT_C002C9C742FF473E | НЕСПРАВЕДЛИВОСТЬ | INTENT | approved |
| INTENT_AB29F2733017A04D | НЕСТАНДАРТНОЕ РЕШЕНИЕ | INTENT | approved |
| INTENT_BEFA82214B9FD5DB | НЕУДАЧНЫЙ ЭКСПЕРИМЕНТ | INTENT | approved |
| INTENT_C1706CF3236E8EBB | НИЧЕГО НЕ ДЕЛАТЬ | INTENT | approved |
| INTENT_B201AD8C21A17381 | НОВАЯ ИДЕЯ | INTENT | approved |
| INTENT_8FB63EC12A60275A | НОЧЁВКА НА ПРИРОДЕ | INTENT | approved |
| INTENT_C770F7E1AFE53BE4 | ОБЪЕЛСЯ | INTENT | approved |
| INTENT_BC2C783E238C6A93 | ОЙ | INTENT | approved |
| GSC-000047 | ОКОНЧАНИЕ УЧЁБЫ | INTENT | approved |
| INTENT_E7B5CE45EC309DA9 | ОНО РАБОТАЕТ | INTENT | approved |
| INTENT_F3BE536F2F5CC801 | ОТБЫВАТЬ НАКАЗАНИЕ | INTENT | approved |
| INTENT_BFA9A3ADE521ADB3 | ОТДОХНУТЬ ОТ РАБОТЫ | INTENT | approved |
| INTENT_86E627DFB79905FB | ОТДЫХ НА ОРБИТЕ | INTENT | approved |
| INTENT_AA9B2703B2D1A9BB | ОТСИДКА | INTENT | approved |
| INTENT_C1CAF7119798357F | ОЦЕНИТЬ ВКУС | INTENT | approved |
| INTENT_31D6D74C3B1D9040 | ОЧЕНЬ ХОЛОДНО | INTENT | approved |
| INTENT_BAFEB2C36AEBEDB7 | ОШЕЛОМЛЕНИЕ | INTENT | approved |
| INTENT_E7C8054BFCB577AE | ПАУЗА | INTENT | approved |
| GSC-000106 | ПЕРВАЯ ПОМОЩЬ | INTENT | approved |
| GSC-000081 | ПЕРЕВОЗКИ | INTENT | approved |
| INTENT_C81C0840E9D84CDC | ПЕРЕРЫВ | INTENT | approved |
| INTENT_7B6C4A5D1F3A866D | ПЕСНЯ | INTENT | approved |
| INTENT_89B9267D24DAB25F | ПЛАН ЕСТЬ | INTENT | approved |
| INTENT_B905DF266B5083C5 | ПЛАНЫ НА БУДУЩЕЕ | INTENT | approved |
| INTENT_92026B259A356EFA | ПЛЯЖНЫЙ ОТДЫХ | INTENT | approved |
| GSC-000074 | ПОЕЗДКА | INTENT | approved |
| INTENT_328D3531563896AC | ПОЕХАЛИ | INTENT | approved |
| INTENT_7FB6344AD8B8F62D | ПОИСК ДРЕВНОСТЕЙ | INTENT | approved |
| INTENT_C7849D3BF20247E4 | ПОЛУЧИЛОСЬ | INTENT | approved |
| GSC-000052 | ПОЛУЧИТЬ ДИПЛОМ | INTENT | approved |
| INTENT_D0E3644CE2E92966 | ПОРА В ПУТЬ | INTENT | approved |
| INTENT_5BEDE46B4E167A2A | ПОСЛЕ ЕДЫ | INTENT | approved |
| GSC-000100 | ПОСТАВИТЬ ДИАГНОЗ | INTENT | approved |
| INTENT_E8B569BC8E2B159D | ПОХОД ЗИМОЙ | INTENT | approved |
| GSC-000091 | ПРИЁМ ПАЦИЕНТА | INTENT | approved |
| INTENT_720A634E6A93BABD | ПРИВАЛ | INTENT | approved |
| GSC-000025 | ПРИВЕТ | INTENT | approved |
| GSC-000020 | ПРИВЕТСТВИЕ | INTENT | approved |
| INTENT_4555CCC6B38D23D5 | ПРИДУМАТЬ | INTENT | approved |
| INTENT_E417FA2848A7EF3E | ПРОБА СНЯТА | INTENT | approved |
| INTENT_0835F048FADEB3F4 | ПРОГРЕСС | INTENT | approved |
| INTENT_5168C6BCD3C6540A | ПРОДУМАННЫЙ ХОД | INTENT | approved |
| INTENT_19568D359BF31DF5 | ПРОДУМЫВАТЬ | INTENT | approved |
| GSC-000038 | ПРОСНУТЬСЯ | INTENT | approved |
| INTENT_E669A1E3D7F6950C | ПУТЕШЕСТВИЕ В ГОРЫ | INTENT | approved |
| GSC-000079 | ПУТЬ | INTENT | approved |
| GSC-000064 | РАБОТА ВОДИТЕЛЯ | INTENT | approved |
| GSC-000092 | РАБОТА ВРАЧА | INTENT | approved |
| INTENT_943B061DADE94820 | РАБОТА ДОСТАЛА | INTENT | approved |
| INTENT_5553F1FA86EDC362 | РАБОТА ЗА КОМПЬЮТЕРОМ | INTENT | approved |
| INTENT_7C06C02BDBCC54EC | РАБОТА НА КУХНЕ | INTENT | approved |
| INTENT_883E189DAC991DD1 | РАБОТА НАД СОБОЙ | INTENT | approved |
| INTENT_79FBE10C994D9122 | РАБОТА С КОДОМ | INTENT | approved |
| INTENT_0115A1BCD52DC7D6 | РАДОВАТЬСЯ ОСЕНИ | INTENT | approved |
| INTENT_425FC617D79C06AA | РАЗВИТИЕ НАВЫКОВ | INTENT | approved |
| INTENT_4659B5B965C0AEF2 | РАЗВЛЕЧЕНИЕ | INTENT | approved |
| INTENT_063855B5925FD243 | РАЗМЫШЛЕНИЯ О МИРЕ | INTENT | approved |
| GSC-000037 | РАЗМЯТЬСЯ | INTENT | approved |
| INTENT_5E2582F3229886F3 | РАЗОБРАТЬСЯ | INTENT | approved |
| INTENT_A56CFA2B4551336B | РАСКРЫТЬ ТАЙНУ | INTENT | approved |
| GSC-000014 | РАССЛАБИТЬСЯ | INTENT | approved |
| GSC-000030 | РАССЛАБЛЕНИЕ | INTENT | approved |
| GSC-000063 | РЕЙС | INTENT | approved |
| INTENT_12D069ADA34DECEB | РЕШАТЬ РАБОЧИЕ ВОПРОСЫ | INTENT | approved |
| INTENT_AAF51A23696FCF99 | РЕШЕНИЕ БИЗНЕС-ВОПРОСОВ | INTENT | approved |
| INTENT_BE4E36E3DC7F4F39 | РИСУЮ КАРТИНУ | INTENT | approved |
| INTENT_B7EF304641EEF426 | РОК-Н-РОЛЛ | INTENT | approved |
| INTENT_A6B7EF01BC2CAA98 | САМОВЫРАЖЕНИЕ | INTENT | approved |
| INTENT_DDAE65DF24E0A177 | САМООБРАЗОВАНИЕ | INTENT | approved |
| INTENT_2C5789EB434B44B4 | СВОБОДА | INTENT | approved |
| GSC-000018 | СЕРДИТАЯ РЕАКЦИЯ | INTENT | approved |
| INTENT_904B1A828D84C2C9 | СЕРЬЁЗНЫЙ ЗВОНОК | INTENT | approved |
| INTENT_C54D05C00BC85B81 | СИЖУ ОТДЫХАЮ | INTENT | approved |
| INTENT_7F96C598B1290C80 | СИЛЬНЫЙ ИСПУГ | INTENT | approved |
| GSC-000013 | СКЕПТИЧЕСКАЯ РЕАКЦИЯ | INTENT | approved |
| INTENT_285764A2BD4AE8EB | СЛЕДСТВИЕ ИДЁТ | INTENT | approved |
| INTENT_E131DE4230C7D309 | СНЕГОПАД | INTENT | approved |
| INTENT_0573C813BBA44131 | СОБИРАЮСЬ В ПОЕЗДКУ | INTENT | approved |
| INTENT_D3BA61A08FCD3F38 | СОГРЕТЬСЯ | INTENT | approved |
| INTENT_53223C86B62EC98B | СОЗЕРЦАНИЕ | INTENT | approved |
| INTENT_54C4DC8912E89E57 | СОРЕВНОВАНИЕ | INTENT | approved |
| INTENT_000A088594E8800F | СПОКОЙНЫЙ ВЕЧЕР | INTENT | approved |
| INTENT_87773A2DCDBA75BC | СПОКОЙНЫЙ ОТДЫХ | INTENT | approved |
| INTENT_2F9C2B2C4CDAE260 | СТАНОВЛЮСЬ СИЛЬНЕЕ | INTENT | approved |
| INTENT_D3102BF2103F3DE3 | СТАТЬ СИЛЬНЕЕ | INTENT | approved |
| INTENT_FEE98E36B9B4FB3E | СЧАСТЬЕ В МЕЛОЧАХ | INTENT | approved |
| INTENT_7912E7F9F42C075E | СЫТ | INTENT | approved |
| INTENT_6D220D868D27AC85 | СЮРПРИЗ | INTENT | approved |
| INTENT_5CE415062C092349 | ТАНЕЦ | INTENT | approved |
| INTENT_6FAE4E338E58BDBD | ТВОРЧЕСКИЙ ПРОЦЕСС | INTENT | approved |
| GSC-000132 | ТЕОРИЯ | INTENT | approved |
| INTENT_DEEBACAB24AD03E7 | ТЕХНИЧЕСКАЯ РАБОТА | INTENT | approved |
| GSC-000065 | ТРАССА | INTENT | approved |
| INTENT_1FB8609FEA88C6E4 | УДАЧНЫЙ ЗАПУСК | INTENT | approved |
| INTENT_E5673AA7733CBF97 | УЗНАЮ НОВОСТИ | INTENT | approved |
| INTENT_B9731DD056B07EEC | УСПЕШНЫЙ | INTENT | approved |
| INTENT_3CE77F836C4173E9 | УСПЕШНЫЙ БИЗНЕС | INTENT | approved |
| INTENT_1906BDF2D4A67919 | УЧЁБА ДОСТАЛА | INTENT | approved |
| INTENT_COZY | УЮТ | INTENT | approved |
| INTENT_91E283D9288C1DFA | УЮТНЫЙ ОТДЫХ | INTENT | approved |
| INTENT_4D86D5F8310AC123 | ФОКУС | INTENT | approved |
| INTENT_DC5C8E0DABD054DF | ФОКУС-ПОКУС | INTENT | approved |
| INTENT_2C74891A8D77E7DB | ХОД КОНЁМ | INTENT | approved |
| GSC-000002 | ХОРОШЕЕ НАСТРОЕНИЕ | INTENT | approved |
| INTENT_27196C61FEA04077 | ХОЧУ В КОСМОС | INTENT | approved |
| INTENT_634DC40138FB3C8F | ЦАРЬ ЖИЗНИ | INTENT | approved |
| INTENT_A841EAFDDD636D88 | ЦЕННАЯ НАХОДКА | INTENT | approved |
| INTENT_DDD82E50B824F3DD | ЦЕННОСТЬ | INTENT | approved |
| INTENT_F2F0B0A33E8E7748 | ЧИНЮ РОБОТА | INTENT | approved |
| INTENT_610A9EF2C23C55C7 | ЧИТАТЬ КНИГУ | INTENT | approved |
| INTENT_F6D994FBB21C3404 | ЧТО-ТО ПОШЛО НЕ ТАК | INTENT | approved |
| INTENT_3FD2E1C32FDFEFC8 | ШИРОКИЙ ВЗГЛЯД | INTENT | approved |
| GSC-000021 | ШУТКА | INTENT | approved |
| INTENT_F7D301598703EAD3 | ЭВРИКА | INTENT | approved |
| INTENT_1CB18CBB55624BF5 | Я В ОТПУСКЕ | INTENT | approved |
| INTENT_CA0F350BEE214538 | Я ЗАМЁРЗ | INTENT | approved |
| INTENT_8F169A8E0819545D | Я ЗОЛ | INTENT | approved |
| MOOD_40A32403AD87D228 | АЗАРТ | MOOD | approved |
| MOOD_B3DBBDD0E78BEABF | БОДРОСТЬ | MOOD | approved |
| GSC-000146 | БОДРЫЙ | MOOD | approved |
| MOOD_1E105ABB7B0B99F9 | ВДОХНОВЕНИЕ | MOOD | approved |
| GSC-000093 | ВДУМЧИВОСТЬ | MOOD | approved |
| MOOD_E2FB73779F519091 | ВЕЛИЧИЕ | MOOD | approved |
| GSC-000137 | ВЛАСТНЫЙ | MOOD | approved |
| MOOD_F2236E285B9AB16A | ВООДУШЕВЛЕНИЕ | MOOD | approved |
| MOOD_463E1CF6DF9027E9 | ВОСТОРГ | MOOD | approved |
| MOOD_39626577CB24A7CC | ВОСХИЩЕНИЕ | MOOD | approved |
| GSC-000157 | ГЕРОИЧЕСКИЙ | MOOD | approved |
| MOOD_EF7BDE5C85390CC6 | ГОРДОСТЬ | MOOD | approved |
| GSC-000152 | ГОТОВЫЙ К ДЕЛУ | MOOD | approved |
| MOOD_64C4226DDAAD7569 | ДЕЛОВИТОСТЬ | MOOD | approved |
| GSC-000075 | ДЕЛОВОЙ НАСТРОЙ | MOOD | approved |
| MOOD_753E4CF9356BA017 | ДЕРЗОСТЬ | MOOD | approved |
| MOOD_BBAE42EC44961EB6 | ДИСКОМФОРТ | MOOD | approved |
| GSC-000143 | ДИСЦИПЛИНИРОВАННЫЙ | MOOD | approved |
| MOOD_1807E5C0E3BBDF30 | ДОБРОЖЕЛАТЕЛЬНОСТЬ | MOOD | approved |
| GSC-000153 | ДОБРОЖЕЛАТЕЛЬНЫЙ | MOOD | approved |
| MOOD_95D26E7AA030537E | ДОВОЛЬСТВО | MOOD | approved |
| GSC-000156 | ЗАБОТЛИВЫЙ | MOOD | approved |
| MOOD_CFE6C6AF04D8BFF7 | ЗАДУМЧИВОСТЬ | MOOD | approved |
| MOOD_EF69F90E76718848 | ЗЛОСТЬ | MOOD | approved |
| MOOD_E5923C0CA30B9900 | ИГРИВОСТЬ | MOOD | approved |
| MOOD_98DAD9BF0EA697A8 | ИНТЕРЕС | MOOD | approved |
| MOOD_369F44D92913F69E | ИРОНИЯ | MOOD | approved |
| GSC-000015 | НЕДОВОЛЬСТВО | MOOD | approved |
| MOOD_32CD68A4997AF6F5 | ОЗАДАЧЕННОСТЬ | MOOD | approved |
| GSC-000125 | ОЗАРЕНИЕ | MOOD | approved |
| MOOD_E1511666A7F4A6D0 | ОПТИМИЗМ | MOOD | approved |
| MOOD_D73034D358D3532D | ОТЧАЯНИЕ | MOOD | approved |
| MOOD_4FF41EFCD09FB514 | ПЕЧАЛЬ | MOOD | approved |
| MOOD_D09B7EADA22069D3 | ПОДОЗРЕНИЕ | MOOD | approved |
| MOOD_BA063B316CCAC0C8 | ПРЕДВКУШЕНИЕ | MOOD | approved |
| GSC-000158 | ПРОФЕССИОНАЛЬНЫЙ | MOOD | approved |
| GSC-000149 | РАБОЧИЙ | MOOD | approved |
| MOOD_02557292CC9A6972 | РАДОСТЬ | MOOD | approved |
| MOOD_C997BCD15AAFB278 | РАЗДРАЖЕНИЕ | MOOD | approved |
| MOOD_C7FDDE313C4467BB | РАССЛАБЛЕННОСТЬ | MOOD | approved |
| MOOD_FACB898D8764EB74 | РАСТЕРЯННОСТЬ | MOOD | approved |
| MOOD_B45041F4D0D21A8C | РЕШИТЕЛЬНОСТЬ | MOOD | approved |
| MOOD_AB955A64AF4ADCD8 | САМОДОВОЛЬСТВО | MOOD | approved |
| MOOD_E6EE5E08CC8B0A30 | САМОУВЕРЕННОСТЬ | MOOD | approved |
| GSC-000140 | СЕРЬЁЗНЫЙ | MOOD | approved |
| MOOD_B2F95E9E00D9A995 | СИМПАТИЯ | MOOD | approved |
| GSC-000009 | СКЕПСИС | MOOD | approved |
| MOOD_6FBC64FBA8252A02 | СКУКА | MOOD | approved |
| MOOD_34B885F2D39678AF | СМЕЛОСТЬ | MOOD | approved |
| GSC-000139 | СОБРАННЫЙ | MOOD | approved |
| MOOD_4280C24EDBDC1118 | СОСРЕДОТОЧЕННОСТЬ | MOOD | approved |
| GSC-000148 | СОСРЕДОТОЧЕННЫЙ | MOOD | approved |
| GSC-000151 | СПОКОЙНЫЙ | MOOD | approved |
| MOOD_C3986D9DAFA07F51 | СПОКОЙСТВИЕ | MOOD | approved |
| MOOD_30EC65C2BD575A9C | СТРАХ | MOOD | approved |
| GSC-000135 | СТРОГИЙ | MOOD | approved |
| GSC-000144 | ТОРЖЕСТВЕННЫЙ | MOOD | approved |
| GSC-000136 | ТРЕБОВАТЕЛЬНЫЙ | MOOD | approved |
| MOOD_7B9D686BA6E937D5 | УВЕРЕННОСТЬ | MOOD | approved |
| GSC-000141 | УВЕРЕННЫЙ | MOOD | approved |
| MOOD_475F7A5AE7B74D71 | УВЛЕЧЁННОСТЬ | MOOD | approved |
| MOOD_8096F9131E782472 | УДИВЛЕНИЕ | MOOD | approved |
| MOOD_B1F4F968CC9C2743 | УДОВЛЕТВОРЕНИЕ | MOOD | approved |
| MOOD_E4EEF0D22E9B4D0F | УДОВОЛЬСТВИЕ | MOOD | approved |
| MOOD_7160BF1AA404E904 | УМИРОТВОРЕНИЕ | MOOD | approved |
| MOOD_1DB1BA6DD04D8F5A | УСТАЛОСТЬ | MOOD | approved |
| GSC-000003 | ХИТРОСТЬ | MOOD | approved |
| GSC-000159 | ХРАБРЫЙ | MOOD | approved |
| MOOD_67056E1BBCCF016E | ШОК | MOOD | approved |
| GSC-000160 | ЭНЕРГИЧНЫЙ | MOOD | approved |
| MOOD_B6E1BC8AEB045E37 | ЭНТУЗИАЗМ | MOOD | approved |
| OBJECT_17F768C49B4F800F | DJ-ПУЛЬТ | OBJECT | approved |
| GSC-000045 | АКАДЕМИЧЕСКАЯ ШАПОЧКА | OBJECT | approved |
| GSC-000105 | АПТЕЧКА | OBJECT | approved |
| OBJECT_786E615D55F343ED | АРТЕФАКТ | OBJECT | approved |
| OBJECT_397609425E1F5F1B | БАГАЖ | OBJECT | approved |
| OBJECT_18C3436DAD8B27A0 | БЛОКНОТ | OBJECT | approved |
| OBJECT_5EDD937FDB689480 | БЛЮДО С ЛОСОСЕМ | OBJECT | approved |
| OBJECT_248C8190417E0E87 | БОКАЛ ШАМПАНСКОГО | OBJECT | approved |
| OBJECT_DE1ECABBFE813BDE | БУБЕН | OBJECT | approved |
| OBJECT_B3947B7B4EAB6C46 | БУКЕТ РОЗ | OBJECT | approved |
| OBJECT_477493F9F67A9C8E | ГАЗЕТА | OBJECT | approved |
| OBJECT_980D3E283972C2DF | ГАМАК | OBJECT | approved |
| OBJECT_B913A875DF140C97 | ГАНТЕЛЬ | OBJECT | approved |
| OBJECT_7BBB9460B7F4F3DB | ГИРЯ | OBJECT | approved |
| OBJECT_082CCE62DCBDFC67 | ГИТАРА | OBJECT | approved |
| OBJECT_AB005F196CE13ECA | ГЛОБУС | OBJECT | approved |
| OBJECT_8CB9CEDB5EDE1E06 | ГОРЯЧИЙ НАПИТОК | OBJECT | approved |
| OBJECT_8E8BE3ED7AC109CD | ГРАФИК | OBJECT | approved |
| GSC-000058 | ГРУЗОВИК | OBJECT | approved |
| OBJECT_E422AB6FD4C07724 | ДЕНЬГИ | OBJECT | approved |
| OBJECT_C2266BE1883D48BA | ДОКАЗАТЕЛЬСТВО | OBJECT | approved |
| OBJECT_9EFAB2084A421F93 | ДОМ | OBJECT | approved |
| OBJECT_5E7381DDAA0380EA | ДОРОЖНЫЕ НАКЛЕЙКИ | OBJECT | approved |
| OBJECT_69DC67413A36B542 | ДОСКА | OBJECT | approved |
| OBJECT_3798B2654BF9CBBE | ДРАГОЦЕННОСТИ | OBJECT | approved |
| OBJECT_2D762BB1185F3B71 | ДРЕВНИЙ АРТЕФАКТ | OBJECT | approved |
| OBJECT_E088CF6E529952F2 | ДРЕВНЯЯ НАХОДКА | OBJECT | approved |
| OBJECT_A0122320E4344B7D | ДРОН | OBJECT | approved |
| OBJECT_B1EFE2D891DAEE24 | ЕДА | OBJECT | approved |
| OBJECT_6BA12091877B3806 | ЗЕМЛЯ | OBJECT | approved |
| OBJECT_D2838C11AF704704 | ИГРАЛЬНЫЕ КАРТЫ | OBJECT | approved |
| OBJECT_A39C7D319EF76A8A | ИЛЛЮМИНАТОР | OBJECT | approved |
| OBJECT_8B186132732BE7B4 | ИСКРЫ | OBJECT | approved |
| GSC-000070 | КАБИНА ГРУЗОВИКА | OBJECT | approved |
| OBJECT_E5AF1347F6AFDF8F | КАМИН | OBJECT | approved |
| OBJECT_EE8FA938D38CB377 | КАРТА | OBJECT | approved |
| OBJECT_9D317B3FE35A260B | КАСТРЮЛЯ | OBJECT | approved |
| OBJECT_5948AC5D796278E3 | КИСТОЧКА | OBJECT | approved |
| OBJECT_69682F813D2ADA8E | КИСТЬ (ИНСТРУМЕНТ) | OBJECT | approved |
| OBJECT_D341B4759D5B0A51 | КНИГА | OBJECT | approved |
| OBJECT_0D2BB0E23442E094 | КОД | OBJECT | approved |
| GSC-000118 | КОЛБА | OBJECT | approved |
| OBJECT_E39B55B062BE8294 | КОЛБЫ | OBJECT | approved |
| OBJECT_3C92A9DDD9C77DB5 | КОМПЬЮТЕР | OBJECT | approved |
| OBJECT_16F256C681FD079B | КРАСКИ | OBJECT | approved |
| OBJECT_C733349A10881007 | КРЕСЛО | OBJECT | approved |
| OBJECT_ECC50715630DEAD7 | КРУЖКА | OBJECT | approved |
| OBJECT_A745D7FDE7A3656F | ЛОСОСЬ | OBJECT | approved |
| OBJECT_924411195825550F | ЛУПА | OBJECT | approved |
| OBJECT_BAB84931B226E59A | МЕШОК С ДЕНЬГАМИ | OBJECT | approved |
| GSC-000123 | МИКРОСКОП | OBJECT | approved |
| OBJECT_9A15CEE5F9A4BDBF | МИКРОФОН | OBJECT | approved |
| OBJECT_F1A90B06DC94ABF2 | МИСКА | OBJECT | approved |
| OBJECT_78E9F27BEB5F1888 | МОБИЛЬНЫЙ ТЕЛЕФОН | OBJECT | approved |
| GSC-000131 | МОЛЕКУЛА | OBJECT | approved |
| OBJECT_6989C51A3C95CAB8 | МОЛЬБЕРТ | OBJECT | approved |
| OBJECT_2F1EB8FB96C43C01 | МОНЕТА | OBJECT | approved |
| OBJECT_F4A8A6195AE9BDDF | НАПИТОК | OBJECT | approved |
| OBJECT_AAE7B317B2C87FBB | НАРЫ | OBJECT | approved |
| OBJECT_DA3E38AECF683D07 | НАУШНИКИ | OBJECT | approved |
| OBJECT_BE08380DF865E034 | НОЖ | OBJECT | approved |
| OBJECT_7F2D8AACDDB9C9F2 | НОУТБУК | OBJECT | approved |
| OBJECT_A30F5F5495924EF1 | ОБРАЗ МИРА | OBJECT | requires_semantic_approval |
| OBJECT_E822811AE090303B | ОСЕННИЕ ЛИСТЬЯ | OBJECT | approved |
| OBJECT_6627FA7BE3F6A5FB | ПАЧКИ ДОЛЛАРОВ | OBJECT | approved |
| OBJECT_2EC0BF371232ADFF | ПЛАНШЕТ | OBJECT | approved |
| OBJECT_E9CC69B90C39BCB4 | ПЛЕД | OBJECT | approved |
| OBJECT_F65417D2C7AE5A36 | ПОЛОВНИК | OBJECT | approved |
| OBJECT_01824250B9747A59 | ПОХОДНОЕ СНАРЯЖЕНИЕ | OBJECT | approved |
| OBJECT_64BA18366FA7A63A | РАБОЧЕЕ МЕСТО | OBJECT | approved |
| OBJECT_39A23AC76A76DD54 | РАБОЧИЙ СТОЛ | OBJECT | approved |
| OBJECT_050C8FC00F6FE4DC | РАСТЕНИЕ | OBJECT | approved |
| GSC-000119 | РЕАКТИВ | OBJECT | approved |
| OBJECT_C2BF84BADC80B2FB | РЕАКТИВЫ | OBJECT | approved |
| GSC-000096 | РЕНТГЕНОВСКИЙ СНИМОК | OBJECT | approved |
| OBJECT_136C7CF208C096BD | РИСУНКИ | OBJECT | approved |
| OBJECT_22714F22C8F8479A | РОБОТ | OBJECT | approved |
| GSC-000069 | РУЛЬ | OBJECT | approved |
| OBJECT_3E4B37B3EAA4185D | РУЧКА | OBJECT | approved |
| OBJECT_08634E3A0980FA4C | РЫБА | OBJECT | approved |
| OBJECT_2B96E149AB086C93 | РЮКЗАК | OBJECT | approved |
| OBJECT_3CCF8F1B314B7BA9 | СВИТКИ | OBJECT | approved |
| OBJECT_2DC04E7220696773 | СИГАРА | OBJECT | approved |
| OBJECT_2D927D74C81250AA | СКОВОРОДА | OBJECT | approved |
| OBJECT_BA56F1CCA7C49BC8 | СЛЕДЫ ЛАП | OBJECT | approved |
| OBJECT_5A0BE1A5F53BB20E | СНЕГ | OBJECT | approved |
| OBJECT_1E33C1B6F408E793 | СОКРОВИЩЕ | OBJECT | approved |
| OBJECT_A71A5AFB1A0CFE6C | СПИСОК ЦЕЛЕЙ | OBJECT | approved |
| OBJECT_570D69ECEFB9FE37 | СТАКАН BOSS | OBJECT | approved |
| GSC-000089 | СТЕТОСКОП | OBJECT | approved |
| OBJECT_8F6BACBCE4C4F513 | СТОЛ | OBJECT | approved |
| OBJECT_D7556A1F1E128CEA | СУНДУК | OBJECT | approved |
| OBJECT_FB9A6CE2781EE99B | ТЕТРАДЬ | OBJECT | approved |
| OBJECT_1AD850FD85B82D10 | ТЕХНИЧЕСКИЙ ЧЕРТЁЖ | OBJECT | approved |
| OBJECT_4E7563A5ED4D64A0 | ТРОН | OBJECT | approved |
| OBJECT_AEF8BB0AAFFF5017 | ТУРИСТИЧЕСКОЕ СНАРЯЖЕНИЕ | OBJECT | approved |
| OBJECT_F334EB48B39A96F5 | ТЮРЕМНАЯ РЕШЁТКА | OBJECT | approved |
| GSC-000059 | ТЯГАЧ | OBJECT | approved |
| OBJECT_0A418CFD97A07935 | УКАЗКА | OBJECT | approved |
| OBJECT_46EC5A3FEA481C15 | УЛИКА | OBJECT | approved |
| OBJECT_BEBD74A76A71043F | УЧЕБНЫЕ ПРИНАДЛЕЖНОСТИ | OBJECT | approved |
| OBJECT_9165ED60A392AE59 | ФЕЙЕРВЕРК | OBJECT | approved |
| OBJECT_FC0A54F9F627B826 | ФОНАРЬ | OBJECT | approved |
| OBJECT_D09DC9A8AE41D7BE | ФОТОАППАРАТ | OBJECT | approved |
| OBJECT_6405419B7F29959C | ФУТБОЛЬНЫЙ МЯЧ | OBJECT | approved |
| OBJECT_19FC05ECF2072E7B | ХОЛСТ | OBJECT | approved |
| OBJECT_88F9AC507D5180F4 | ЦЕПЬ | OBJECT | approved |
| OBJECT_950B84951670EEDB | ЧЕК-ЛИСТ | OBJECT | approved |
| OBJECT_DB622F6CFB57905B | ЧЕМОДАНЫ | OBJECT | approved |
| OBJECT_40EAF9E99282BB2F | ШАХМАТНАЯ ДОСКА | OBJECT | approved |
| OBJECT_F72019C82433CEA6 | ШАХМАТНЫЕ ФИГУРЫ | OBJECT | approved |
| OBJECT_1F51D90E60F35336 | ШАХМАТНЫЙ КОНЬ | OBJECT | approved |
| OBJECT_D6A9723E4BC6D1EB | ШПАГА | OBJECT | approved |
| GSC-000113 | ЩЕНОК | OBJECT | approved |
| OBJECT_3236B57FA1C4ECE6 | ЭКСПЕДИЦИОННОЕ СНАРЯЖЕНИЕ | OBJECT | approved |
| OBJECT_02E63B1F5A51D7E0 | ЭСКИЗЫ | OBJECT | approved |
| ROLE_C1B975CACC285792 | DJ | ROLE | approved |
| ROLE_A7A9085544B106D8 | IT-СПЕЦИАЛИСТ | ROLE | approved |
| ROLE_D8CECA661BD8BC6D | АВАНТЮРИСТ | ROLE | approved |
| ROLE_F465A04DDAC5AEDF | АЙТИШНИК | ROLE | approved |
| ROLE_25B256E3E10700A7 | АРХЕОЛОГ | ROLE | approved |
| ROLE_1EB4969421060DD7 | АСТРОНАВТ | ROLE | approved |
| ROLE_F123E9BAE9F824CA | БЕГУН | ROLE | approved |
| ROLE_8057399F6BA54098 | БИЗНЕСМЕН | ROLE | approved |
| GSC-000108 | ВЕТЕРИНАР | ROLE | approved |
| GSC-000133 | ВОЕННЫЙ | ROLE | approved |
| GSC-000083 | ВРАЧ | ROLE | approved |
| GSC-000039 | ВЫПУСКНИК | ROLE | approved |
| GSC-000134 | ГЕНЕРАЛ | ROLE | approved |
| ROLE_7CA1CED1F48B1A84 | ГИТАРИСТ | ROLE | approved |
| GSC-000053 | ДАЛЬНОБОЙЩИК | ROLE | approved |
| ROLE_CFDE4DAC31CAB8E3 | ДЕТЕКТИВ | ROLE | approved |
| ROLE_60D11708FBA97F4D | ДИДЖЕЙ | ROLE | approved |
| ROLE_4D7142172A355C30 | ЗАКЛЮЧЁННЫЙ | ROLE | approved |
| ROLE_9845798BCC1484AD | ИЗОБРЕТАТЕЛЬ | ROLE | approved |
| ROLE_409AD8297017AB78 | ИМПЕРАТОР | ROLE | approved |
| ROLE_06DD312B91F4E2C5 | ИНТЕЛЛЕКТУАЛ | ROLE | approved |
| ROLE_C755DE681011919A | КОДЕР | ROLE | approved |
| ROLE_24CF54E61503FC9E | КОРОЛЬ | ROLE | approved |
| ROLE_COSMONAUT | КОСМОНАВТ | ROLE | approved |
| ROLE_6A2EBD606A64B678 | МУЗЫКАНТ | ROLE | approved |
| ROLE_976035196B137992 | МУШКЕТЁР | ROLE | approved |
| ROLE_1739C39D8AD5F72F | ОФИСНЫЙ РАБОТНИК | ROLE | approved |
| GSC-000142 | ПАРАДНЫЙ | ROLE | approved |
| ROLE_EC237DC7211D6334 | ПЕВЕЦ | ROLE | approved |
| ROLE_86DEF06826CB44D8 | ПЛАНИРОВЩИК | ROLE | approved |
| ROLE_D58CEAA21835A10B | ПОВАР | ROLE | approved |
| GSC-000150 | ПОЖАРНЫЙ | ROLE | approved |
| ROLE_73572DBB1F768855 | ПРОГРАММЕР | ROLE | approved |
| ROLE_PROGRAMMER | ПРОГРАММИСТ | ROLE | approved |
| ROLE_439AD5B6A9D6DFF7 | ПУТЕШЕСТВЕННИК | ROLE | approved |
| GSC-000147 | РАДИСТ | ROLE | approved |
| ROLE_85D9875D37DD4781 | РАЗРАБОТЧИК | ROLE | approved |
| ROLE_4AF302C5D5F6AADD | РОБОТОТЕХНИК | ROLE | approved |
| ROLE_51AC0D08DAFBEE6C | РУКОВОДИТЕЛЬ | ROLE | approved |
| GSC-000138 | СОЛДАТ | ROLE | approved |
| GSC-000155 | СПАСАТЕЛЬ | ROLE | approved |
| ROLE_03C925C571C824D3 | СПОРТСМЕН | ROLE | approved |
| ROLE_BD9F3D7588083560 | СЫЩИК | ROLE | approved |
| GSC-000145 | ТАНКИСТ | ROLE | approved |
| ROLE_TOURIST | ТУРИСТ | ROLE | approved |
| GSC-000114 | УЧЁНЫЙ | ROLE | approved |
| ROLE_FD662C9FA7BF5AAB | УЧЕНИК | ROLE | approved |
| ROLE_61C48A46BFD3347B | ФОКУСНИК | ROLE | approved |
| ROLE_53DAF8A564E12962 | ФУТБОЛИСТ | ROLE | approved |
| ROLE_CA30F9F1668A2C51 | ХУДОЖНИК | ROLE | approved |
| ROLE_EF1D25FEA3F0FF75 | ШАХМАТИСТ | ROLE | approved |
| ROLE_C9FD1C933DA0BC3F | ШЕФ-ПОВАР | ROLE | approved |
| SCENARIO_CONCEPT_348D44912B4824F8 | КАРТОЧНЫЙ ФОКУС | SCENARIO_CONCEPT | approved |
| SCENARIO_CONCEPT_16C40B8FD01FB81F | НАБЛЮДЕНИЕ ИЗ ИЛЛЮМИНАТОРА | SCENARIO_CONCEPT | approved |
| SCENARIO_CONCEPT_EA0225082E6F37A9 | ОТДЫХ В ГАМАКЕ | SCENARIO_CONCEPT | approved |
| SCENARIO_CONCEPT_C10D38282E358033 | ПРЕЗЕНТАЦИЯ ПЛАНОВ | SCENARIO_CONCEPT | approved |
| SCENARIO_CONCEPT_471DD34DB96AE721 | ТЕЛЕФОННЫЙ РАЗГОВОР | SCENARIO_CONCEPT | approved |
| SCENARIO_CONCEPT_649534D021EDEB43 | ФОКУС С МОНЕТОЙ | SCENARIO_CONCEPT | approved |
| SCENARIO_CONCEPT_D6976D94344FAB02 | ХИМИЧЕСКИЙ ЭКСПЕРИМЕНТ | SCENARIO_CONCEPT | approved |
| SCENARIO_CONCEPT_660B1DF7321BFCF9 | ЧТЕНИЕ У КАМИНА | SCENARIO_CONCEPT | approved |
| SUBJECT_ANIMAL | ЖИВОТНОЕ | SUBJECT | approved |
| SUBJECT_CAT | КОТ | SUBJECT | approved |
| GSC-000154 | КОТЁНОК | SUBJECT | approved |
| SUBJECT_CHARACTER | ПЕРСОНАЖ | SUBJECT | approved |
| SUBJECT_3BBF9E899486B9C1 | ПТИЦА | SUBJECT | approved |
| SUBJECT_E480652036A8EF51 | СОБАКА | SUBJECT | approved |
| THEME_52BF42AB27D88CAB | IT | THEME | approved |
| THEME_996FE7D365047A2C | АРХЕОЛОГИЯ | THEME | approved |
| THEME_D847FDFB376D6E38 | БЕГ | THEME | approved |
| THEME_FFEC307A7731C4AC | БИЗНЕС | THEME | approved |
| THEME_44038E89F5D2F69D | БЛАГОПОЛУЧИЕ | THEME | approved |
| THEME_932128E029C04C1E | БОГАТСТВО | THEME | approved |
| THEME_207868CD3D72C1C1 | БОЛЬШИЕ ПЛАНЫ | THEME | approved |
| THEME_2436E96A974AF500 | БУДУЩЕЕ | THEME | approved |
| GSC-000109 | ВЕТЕРИНАРИЯ | THEME | approved |
| THEME_5601A6C28EE2381C | ВЕЧЕРИНКА | THEME | approved |
| THEME_9B9CC6E465118183 | ВЛАСТЬ | THEME | approved |
| GSC-000066 | ВОЖДЕНИЕ | THEME | approved |
| THEME_A1E06872C94F21CB | ВОКАЛ | THEME | approved |
| GSC-000042 | ВЫПУСК | THEME | approved |
| GSC-000049 | ВЫПУСКНОЙ | THEME | approved |
| THEME_B8A8AAC786EFAE15 | ВЫСОКИЙ СТАТУС | THEME | approved |
| THEME_238AF8DB50535FA8 | ВЫСТУПЛЕНИЕ | THEME | approved |
| THEME_12B811855AFBA693 | ГЕРОЙ | THEME | approved |
| THEME_F19F596788DBA8B0 | ГОРЫ | THEME | approved |
| GSC-000056 | ГРУЗОПЕРЕВОЗКИ | THEME | approved |
| GSC-000054 | ДАЛЬНОБОЙ | THEME | approved |
| GSC-000031 | ДВИЖЕНИЕ | THEME | approved |
| THEME_8F5AB6AAB8E4CB82 | ДЕГУСТАЦИЯ | THEME | approved |
| GSC-000087 | ДИАГНОСТИКА | THEME | approved |
| THEME_087F27B8A8D6B703 | ДИЗАЙН | THEME | approved |
| GSC-000043 | ДИПЛОМ | THEME | approved |
| THEME_0ED69F70DA5C6156 | ДОМАШНЕЕ ЗАДАНИЕ | THEME | approved |
| THEME_F0AF9FE5D8D46290 | ДОМАШНИЙ УЮТ | THEME | approved |
| THEME_4296809D62037409 | ДОРОГА | THEME | approved |
| THEME_57FD0B8E1F29CADD | ДРЕВНОСТИ | THEME | approved |
| GSC-000019 | ДРУЖЕЛЮБИЕ | THEME | approved |
| THEME_910442ACA72C927A | ДРУЖЕСКОЕ СОПЕРНИЧЕСТВО | THEME | approved |
| THEME_0D9AF1F172A8043C | ДУЭЛЬ | THEME | approved |
| THEME_3FE76422723B8273 | ЖИВОПИСЬ | THEME | approved |
| THEME_45801EE1D3183644 | ЗАКЛЮЧЕНИЕ | THEME | approved |
| THEME_E63979117E68ACF3 | ЗВЁЗДНОЕ НЕБО | THEME | approved |
| THEME_CC6F774A0ACB633F | ЗДОРОВЫЙ ОБРАЗ ЖИЗНИ | THEME | approved |
| THEME_2730EE1C6EB21A9D | ЗИМА | THEME | approved |
| THEME_B60E275F0739EE7F | ЗИМНИЙ ПОХОД | THEME | approved |
| THEME_7267CC168DB88E42 | ЗНАНИЯ | THEME | approved |
| GSC-000027 | ИГРА | THEME | approved |
| THEME_4EC116834CA7D35F | ИДЕЯ | THEME | approved |
| THEME_89A3FEFCDF7F48B6 | ИЗОБРЕТЕНИЕ | THEME | approved |
| THEME_67ACB97B06DFAB58 | ИЛЛЮЗИЯ | THEME | approved |
| THEME_EFF70CBC64B74F65 | ИНВЕСТИЦИИ | THEME | approved |
| THEME_FDE67E2EEAC87940 | ИНЖЕНЕРИЯ | THEME | approved |
| THEME_AA852C784EB748D8 | ИНТЕЛЛЕКТ | THEME | approved |
| THEME_4CE3D3B0E1054D11 | ИСКУССТВО | THEME | approved |
| THEME_CF24381FDF4BEEB8 | ИСПУГ | THEME | approved |
| THEME_1309EF75AF98B860 | ИСТИНА | THEME | approved |
| THEME_47F7958BCC34F7F5 | ИСТОРИЯ | THEME | approved |
| THEME_B1F380E7F9A3D199 | КОМФОРТ | THEME | approved |
| THEME_A7511BEBA8E4B7D1 | КОНЦЕРТ | THEME | approved |
| THEME_A5DC57FAE7C344FE | КОРОЛЕВСКАЯ ВЛАСТЬ | THEME | approved |
| THEME_22A4050CEE56FF01 | КОСМИЧЕСКИЙ ПОЛЁТ | THEME | approved |
| THEME_3645C016228277ED | КОСМОС | THEME | approved |
| THEME_7DA73E109A83CB1D | КРИМИНАЛЬНАЯ СТИЛИЗАЦИЯ | THEME | approved |
| THEME_8CD17FB81C91D808 | КРУГОЗОР | THEME | approved |
| THEME_436F712ACEEC24A9 | КУЛИНАРИЯ | THEME | approved |
| THEME_B950D99DCF544C66 | КУХНЯ | THEME | approved |
| GSC-000115 | ЛАБОРАТОРИЯ | THEME | approved |
| THEME_1E41385677C74758 | ЛЕТО | THEME | approved |
| GSC-000103 | ЛЕЧЕНИЕ | THEME | approved |
| THEME_E00C85E80A5E30E5 | ЛИСТОПАД | THEME | approved |
| THEME_03AB9EF5B045F224 | МАГИЯ | THEME | approved |
| GSC-000084 | МЕДИЦИНА | THEME | approved |
| THEME_7B42E6492F24AC73 | МЕЧТА | THEME | approved |
| GSC-000121 | МИКРОСКОПИЯ | THEME | approved |
| THEME_D690E8F9A6E38687 | МОРЕ | THEME | approved |
| THEME_2A8800587EE19E7A | МОРОЗ | THEME | approved |
| THEME_18B0A75EC4654D1B | МОТИВАЦИЯ | THEME | approved |
| THEME_51C1D360F9938B3E | МУЗИЦИРОВАНИЕ | THEME | approved |
| THEME_583D7926FF8A8803 | МУЗЫКА | THEME | approved |
| THEME_5945F4FCE644FE0B | НАВИГАЦИЯ | THEME | approved |
| THEME_0CEB5D3A35CA4322 | НАКАЗАНИЕ | THEME | approved |
| THEME_4D6E8ABDBD17E9C1 | НАСТОЛЬНАЯ ИГРА | THEME | approved |
| THEME_276517D99E0E5781 | НАУКА | THEME | approved |
| THEME_8E535CB5F44C66A4 | НЕЛОВКОСТЬ | THEME | approved |
| THEME_9DA6CEC55134F953 | НЕОЖИДАННОСТЬ | THEME | approved |
| THEME_E12D4FF69EE2202F | НЕСВОБОДА | THEME | approved |
| THEME_05715101EFD3EAF7 | НЕСТАНДАРТНОЕ МЫШЛЕНИЕ | THEME | approved |
| THEME_4105DF44E155F6DA | НОВОСТИ | THEME | approved |
| THEME_41BCF7B4FCC47193 | НОВЫЕ МЕСТА | THEME | approved |
| THEME_B5548A38834A7F95 | НОЧЬ | THEME | approved |
| GSC-000040 | ОБРАЗОВАНИЕ | THEME | approved |
| THEME_79ADB5C50F831B17 | ОБУЧЕНИЕ | THEME | approved |
| GSC-000022 | ОБЩЕНИЕ | THEME | approved |
| THEME_16827D589E6F04AB | ОКРУЖАЮЩИЙ МИР | THEME | approved |
| THEME_ED7C5991004A637B | ОРГАНИЗАЦИЯ | THEME | approved |
| THEME_1A44B5783FB2F8DF | ОСЕНЬ | THEME | approved |
| GSC-000086 | ОСМОТР | THEME | approved |
| THEME_84C951CDFB09287A | ОТДЫХ | THEME | approved |
| THEME_049373C82A446E3C | ОТКРЫТИЕ | THEME | approved |
| GSC-000127 | ОТКРЫТИЯ | THEME | approved |
| THEME_8FED8298B59F6DBA | ОТПУСК | THEME | approved |
| THEME_459C594A3F102A7A | ОФИС | THEME | approved |
| THEME_45774841504BE89C | ПЕРЕГОВОРЫ | THEME | approved |
| THEME_7283A241D4F020FB | ПЕРЕДЫШКА | THEME | approved |
| THEME_F72EF4FEEA559BAF | ПЕРКУССИЯ | THEME | approved |
| THEME_C89D63D604FEA567 | ПЛАН | THEME | approved |
| THEME_3E5EB2C94A31745B | ПЛАНЕТА | THEME | approved |
| THEME_E1B29D7BB8D97A6E | ПЛАНИРОВАНИЕ | THEME | approved |
| THEME_08C031DB630454E5 | ПЛЯЖ | THEME | approved |
| THEME_BFE4DB066BAE3066 | ПОГОДА | THEME | approved |
| THEME_87FD3E3BAEC40A10 | ПОДАРОК | THEME | approved |
| THEME_A5D192B523FF7EE0 | ПОИСК | THEME | approved |
| THEME_D000AF015757BB61 | ПОИСК УЛИК | THEME | approved |
| THEME_AF5993DDFE0BF104 | ПОЛЁТ | THEME | approved |
| GSC-000102 | ПОМОЩЬ | THEME | approved |
| GSC-000110 | ПОМОЩЬ ЖИВОТНЫМ | THEME | approved |
| THEME_ACA1001C1B09CCFF | ПОХОД | THEME | approved |
| THEME_552D043416FD4144 | ПРАЗДНИК | THEME | approved |
| GSC-000085 | ПРИЁМ | THEME | approved |
| THEME_C1D5CD89F9F80EB4 | ПРИГОТОВЛЕНИЕ ЕДЫ | THEME | approved |
| THEME_DA5F4A7367715EA7 | ПРИКЛЮЧЕНИЕ | THEME | approved |
| THEME_D3B746D1460E187C | ПРИНЯТИЕ РЕШЕНИЙ | THEME | approved |
| THEME_BDFA873EF94AB241 | ПРИРОДА | THEME | approved |
| GSC-000035 | ПРОБУЖДЕНИЕ | THEME | approved |
| THEME_1A434BBADE10EE33 | ПРОГРАММИРОВАНИЕ | THEME | approved |
| GSC-000032 | ПРОГУЛКА | THEME | approved |
| THEME_B75F5FF1E8660E90 | ПРОДУКТИВНОСТЬ | THEME | approved |
| THEME_F3A4A60573BA7017 | ПУТЕШЕСТВИЕ | THEME | approved |
| THEME_02F91ACED1321F3F | РАБОТА | THEME | approved |
| THEME_8C303DC50D19FD29 | РАЗВИТИЕ | THEME | approved |
| THEME_99B83A867DBB9F67 | РАЗМЫШЛЕНИЯ | THEME | approved |
| THEME_286759E62443583D | РАСКОПКИ | THEME | approved |
| THEME_A60F2B78F3FD0331 | РАССЛЕДОВАНИЕ | THEME | approved |
| THEME_43C94066FA737083 | РЕАКЦИЯ | THEME | approved |
| GSC-000094 | РЕНТГЕН | THEME | approved |
| THEME_D5015A9F2AF91583 | РЕШЕНИЕ ЗАДАЧ | THEME | approved |
| THEME_E88610061840B1D2 | РИСК | THEME | approved |
| THEME_3A04D6D719D200C5 | РИТМ | THEME | approved |
| THEME_4A725D17A742110A | РОБОТОТЕХНИКА | THEME | approved |
| THEME_27C343511E57E4D9 | РОК | THEME | approved |
| THEME_741187A4EB51C78C | РОМАНТИКА | THEME | approved |
| THEME_812ED1D5F4BB097D | РОСКОШЬ | THEME | approved |
| THEME_B6BDE0D660A957C8 | РОСТ | THEME | approved |
| THEME_F11DF2687172BF6C | РУКОВОДСТВО | THEME | approved |
| THEME_A2E5317EDCEB4152 | САМОРАЗВИТИЕ | THEME | approved |
| THEME_5D86D9B23D850F0B | СВИДАНИЕ | THEME | approved |
| THEME_B49569FD35DB3C04 | СИЛОВАЯ ТРЕНИРОВКА | THEME | approved |
| THEME_9C80602B337CD9B2 | СЛЕДСТВИЕ | THEME | approved |
| GSC-000010 | СОМНЕНИЕ | THEME | approved |
| THEME_17312424270A71F4 | СОН | THEME | approved |
| THEME_FC6031C23D7F273B | СОСТОЯТЕЛЬНОСТЬ | THEME | approved |
| THEME_274FCD8C7C6ADAF9 | СПИСОК ДЕЛ | THEME | approved |
| THEME_498A56D52ABF8EA4 | СПОРТ | THEME | approved |
| THEME_A3FB404C6DA6A917 | СРОК | THEME | approved |
| THEME_C3BB74181993A494 | СТАТУС | THEME | approved |
| THEME_7ECD3F3BB5C56972 | СТРАТЕГИЯ | THEME | approved |
| THEME_F8A8251601E2B48D | СЦЕНИЧЕСКОЕ ШОУ | THEME | approved |
| THEME_60662A464EB3247F | СЧАСТЬЕ | THEME | approved |
| THEME_D011B0259FB9AA55 | ТАЙНА | THEME | approved |
| THEME_96A940D086EBA72A | ТАКТИКА | THEME | approved |
| THEME_C49A50A21089E1BE | ТАНЦЫ | THEME | approved |
| THEME_6F6D098B0937EA04 | ТВОРЧЕСТВО | THEME | approved |
| THEME_BA5C4E1CB284A918 | ТЕПЛО | THEME | approved |
| THEME_6BAA043CDFE96790 | ТЕХНИЧЕСКОЕ ТВОРЧЕСТВО | THEME | approved |
| THEME_F39E41B90F8E162F | ТЕХНОЛОГИИ | THEME | approved |
| GSC-000055 | ТРАНСПОРТ | THEME | approved |
| THEME_87D8756461DFA67B | ТРЕНИРОВКА | THEME | approved |
| THEME_A2434647CF075571 | ТУРИЗМ | THEME | approved |
| THEME_34255AD558FAF1AD | ТЮРЬМА | THEME | approved |
| THEME_460F30189B737F3F | УДАЛЁННАЯ РАБОТА | THEME | approved |
| GSC-000041 | УНИВЕРСИТЕТ | THEME | approved |
| THEME_C84C319EAA21C5CB | УПРАВЛЕНИЕ | THEME | approved |
| THEME_2500CEA69B64EB26 | УСПЕХ | THEME | approved |
| THEME_950B64243E67C0B8 | УТРО | THEME | approved |
| THEME_1F8833A8A58FCD5D | УЧЁБА | THEME | approved |
| GSC-000126 | ФИЗИКА | THEME | approved |
| THEME_2F87238C5B281CA0 | ФИТНЕС | THEME | approved |
| THEME_DE8BE0B834374501 | ФОКУСЫ | THEME | approved |
| THEME_34F284F8701E7E66 | ФУТБОЛ | THEME | approved |
| THEME_5051DB8F6B403AA4 | ХИМИЯ | THEME | approved |
| THEME_447F867EA718FA92 | ЦЕЛЬ | THEME | approved |
| THEME_F84DE4D9707AB929 | ЧЕСТЬ | THEME | approved |
| THEME_CD65BB480574CA7C | ЧТЕНИЕ | THEME | approved |
| THEME_F7C87789074FB283 | ШАХМАТЫ | THEME | approved |
| THEME_925AE62BB4573092 | ШОУ | THEME | approved |
| THEME_54FFEFED80E43F63 | ЭКСПЕДИЦИЯ | THEME | approved |
| THEME_C7F45CD55FB86876 | ЭКСПЕРИМЕНТ | THEME | approved |
| THEME_4A6FC880A40A33CC | ЭЛЕКТРОНИКА | THEME | approved |
| THEME_649D46872F7FBD9F | ЭМОЦИИ | THEME | approved |

## Все SYNONYM

- КОСМОНАВТ → АСТРОНАВТ (approved_semantic_review).
- ПРОГРАММИСТ → КОДЕР (approved_semantic_review).
- ДЕТЕКТИВ → СЫЩИК (approved_semantic_review).
- ДИДЖЕЙ → DJ (approved_semantic_review).
- КИСТЬ (ИНСТРУМЕНТ) → КИСТОЧКА (approved_semantic_review).
- ПРОГРАММИСТ → РАЗРАБОТЧИК (approved_software_developer_scope; constraints={"bidirectional_only_when_scope_matches": true, "context_any_concept_ids": ["THEME_52BF42AB27D88CAB", "THEME_1A434BBADE10EE33", "OBJECT_0D2BB0E23442E094"], "scope": "software_developer", "unscoped_synonym_forbidden": true}).

## Все COLLOQUIAL

- IT-СПЕЦИАЛИСТ → АЙТИШНИК (user_control_example).
- ПРОГРАММИСТ → ПРОГРАММЕР (user_control_example).

## Все BROADER

- КОТ → ЖИВОТНОЕ (curated_direct_relation).
- СОБАКА → ЖИВОТНОЕ (curated_direct_relation).
- ПТИЦА → ЖИВОТНОЕ (curated_direct_relation).
- ПРОГРАММИСТ → IT-СПЕЦИАЛИСТ (curated_direct_relation).
- ГИТАРИСТ → МУЗЫКАНТ (curated_direct_relation).
- ПЕВЕЦ → МУЗЫКАНТ (curated_direct_relation).
- ФУТБОЛИСТ → СПОРТСМЕН (curated_direct_relation).
- БЕГУН → СПОРТСМЕН (curated_direct_relation).
- ШЕФ-ПОВАР → ПОВАР (curated_direct_relation).
- НОУТБУК → КОМПЬЮТЕР (curated_direct_relation).
- ПОЛЕВАЯ ШЛЯПА → ШЛЯПА (curated_direct_relation).
- ЗАЩИТНЫЕ ОЧКИ → ОЧКИ (curated_direct_relation).
- ТЁМНЫЕ ОЧКИ → ОЧКИ (curated_direct_relation).
- СОЛНЕЧНЫЕ ОЧКИ → ОЧКИ (curated_direct_relation).
- БЕЛАЯ РУБАШКА → РУБАШКА (curated_direct_relation).
- ЧЁРНЫЙ ДЕЛОВОЙ КОСТЮМ → ДЕЛОВОЙ КОСТЮМ (curated_direct_relation).

## Все NARROWER

- ЖИВОТНОЕ → КОТ (curated_direct_relation).
- ЖИВОТНОЕ → СОБАКА (curated_direct_relation).
- ЖИВОТНОЕ → ПТИЦА (curated_direct_relation).
- IT-СПЕЦИАЛИСТ → ПРОГРАММИСТ (curated_direct_relation).
- МУЗЫКАНТ → ГИТАРИСТ (curated_direct_relation).
- МУЗЫКАНТ → ПЕВЕЦ (curated_direct_relation).
- СПОРТСМЕН → ФУТБОЛИСТ (curated_direct_relation).
- СПОРТСМЕН → БЕГУН (curated_direct_relation).
- ПОВАР → ШЕФ-ПОВАР (curated_direct_relation).
- КОМПЬЮТЕР → НОУТБУК (curated_direct_relation).
- ШЛЯПА → ПОЛЕВАЯ ШЛЯПА (curated_direct_relation).
- ОЧКИ → ЗАЩИТНЫЕ ОЧКИ (curated_direct_relation).
- ОЧКИ → ТЁМНЫЕ ОЧКИ (curated_direct_relation).
- ОЧКИ → СОЛНЕЧНЫЕ ОЧКИ (curated_direct_relation).
- РУБАШКА → БЕЛАЯ РУБАШКА (curated_direct_relation).
- ДЕЛОВОЙ КОСТЮМ → ЧЁРНЫЙ ДЕЛОВОЙ КОСТЮМ (curated_direct_relation).

## Все RELATED

- КОСМОНАВТ → КОСМОС (curated_direct_relation).
- КОСМОНАВТ → КОСМИЧЕСКИЙ ПОЛЁТ (curated_direct_relation).
- ПРОГРАММИСТ → ПРОГРАММИРОВАНИЕ (curated_direct_relation).
- ПРОГРАММИСТ → IT (curated_direct_relation).
- ПРОГРАММИСТ → КОД (curated_direct_relation).
- ПРОГРАММИСТ → КОМПЬЮТЕР (curated_direct_relation).
- ПРОГРАММИСТ → НОУТБУК (curated_direct_relation).
- ТУРИСТ → ТУРИЗМ (curated_direct_relation).
- ТУРИСТ → ПУТЕШЕСТВИЕ (curated_direct_relation).
- ТУРИСТ → ПОХОД (curated_direct_relation).
- ТУРИСТ → РЮКЗАК (curated_direct_relation).
- УЮТ → ДОМ (curated_direct_relation).
- УЮТ → ГОРЯЧИЙ НАПИТОК (curated_direct_relation).
- УЮТ → ОТДЫХ (curated_direct_relation).
- УЮТ → ТЕПЛО (curated_direct_relation).
- УЮТ → ЧТЕНИЕ (curated_direct_relation).
- ГИТАРИСТ → ГИТАРА (curated_direct_relation).
- АРХЕОЛОГ → РАСКОПКИ (curated_direct_relation).
- АРХЕОЛОГ → АРХЕОЛОГИЯ (curated_direct_relation).
- ПОВАР → КУЛИНАРИЯ (curated_direct_relation).
- ПОВАР → ПРИГОТОВЛЕНИЕ ЕДЫ (curated_direct_relation).
- ПОВАР → СКОВОРОДА (curated_direct_relation).
- ПОВАР → КАСТРЮЛЯ (curated_direct_relation).
- ДЕТЕКТИВ → РАССЛЕДОВАНИЕ (curated_direct_relation).
- ДЕТЕКТИВ → ПОИСК УЛИК (curated_direct_relation).
- ДЕТЕКТИВ → ЛУПА (curated_direct_relation).
- ДЕТЕКТИВ → УЛИКА (curated_direct_relation).
- ХУДОЖНИК → ЖИВОПИСЬ (curated_direct_relation).
- ХУДОЖНИК → МОЛЬБЕРТ (curated_direct_relation).
- ХУДОЖНИК → ХОЛСТ (curated_direct_relation).
- ФУТБОЛИСТ → ФУТБОЛ (curated_direct_relation).
- ФУТБОЛИСТ → ФУТБОЛЬНЫЙ МЯЧ (curated_direct_relation).
- ПЕВЕЦ → МИКРОФОН (curated_direct_relation).
- ФОКУСНИК → ФОКУСЫ (curated_direct_relation).
- ФОКУСНИК → ИЛЛЮЗИЯ (curated_direct_relation).
- ШАХМАТИСТ → ШАХМАТЫ (curated_direct_relation).
- РОБОТОТЕХНИК → РОБОТОТЕХНИКА (curated_direct_relation).
- РОБОТОТЕХНИК → РОБОТ (curated_direct_relation).
- ПУТЕШЕСТВЕННИК → ПУТЕШЕСТВИЕ (curated_direct_relation).
- БЕГУН → БЕГ (curated_direct_relation).
- ДИДЖЕЙ → DJ-ПУЛЬТ (curated_direct_relation).
- ТУРИСТ → ПУТЕШЕСТВЕННИК (approved_semantic_review).
- ДОВОЛЬСТВО → УДОВЛЕТВОРЕНИЕ (approved_semantic_review).
- СПОКОЙСТВИЕ → УМИРОТВОРЕНИЕ (approved_semantic_review).
- ХИМИЧЕСКИЙ ЭКСПЕРИМЕНТ → ХИМИЯ (curated_direct_relation).
- КАРТОЧНЫЙ ФОКУС → ФОКУСЫ (curated_direct_relation).
- ФОКУС С МОНЕТОЙ → ФОКУСЫ (curated_direct_relation).
- ЧТЕНИЕ У КАМИНА → ЧТЕНИЕ (curated_direct_relation).
- ОТДЫХ В ГАМАКЕ → ОТДЫХ (curated_direct_relation).

## REQUIRES_SEMANTIC_APPROVAL

1. **ОБРАЗ МИРА** (OBJECT_A30F5F5495924EF1): Не определено, является ли это самостоятельным объектом, изображением планеты или представлением об окружающем мире.

## Повторный integrity report

- 132 уникальных image_id; все исходные карточки импортированы.
- Все нормализации перечислены выше; display_name, Sections, character_assignment и художественные файлы не менялись.
- Все source-field bindings разрешаются через постоянный concept_id registry.
- Registry допускает одинаковый canonical у разных sense_key и один concept_id для нескольких полей.
- Неизвестное или неоднозначное понятие останавливает сборку; ID не вычисляется из canonical/type.
- Все ссылки на active concept_id разрешены; ID и sense_key уникальны.
- В BROADER нет циклов; ЖИВОТНОЕ ↔ ПЕРСОНАЖ отсутствует.
- ТЁМНЫЕ и СОЛНЕЧНЫЕ ОЧКИ не слиты; обе разновидности имеют BROADER → ОЧКИ.
- RELATED не является доказательством наличия объекта, темы или роли.
- STYLE отмечен как absent_in_source_cards и не включён в unresolved.
- 117 RK17 character bindings подтверждены; OTHER не назначен Чеддером.

## Созданные и изменённые файлы

- global_search_dictionary.v1.json — authoritative dictionary, approved.
- build_search_dictionary.py — generator, читающий permanent registry.
- concept_id_registry.json — permanent ID and source-binding registry.
- concept_id_migration.json — rename/retype/redirect migration and changed concept_id list.
- semantic_cards.json — нормализованные 132 карточки.
- image_concept_bindings.json — явные image-field → concept_id bindings.
- GLOBAL_SEARCH_DICTIONARY_REPORT.md — этот производный отчёт.
- migrate_concept_id_registry.py — одноразовая воспроизводимая миграция legacy IDs.
- migration-source/*.json — неизменяемые снимки предыдущей сборки для повторения миграции.
- source-cards/*.json — исходные утверждённые карточки без художественных файлов.
- validate_search_dictionary.py — независимая проверка утверждённых решений и целостности.
