# -*- encoding: utf-8 -*-


def translate(name, replase_space="_"):
    # Заменяем пробелы и преобразуем строку к нижнему регистру
    #name = name.replace(' ', '-').lower()
    if replase_space:
        name = name.replace(' ', replase_space) # Заменяем пробелы

    #
    transtable = (
        ## Большие буквы
        (u"Щ", u"SCH"),
        # two-symbol
        (u"Ё", u"YO"),
        (u"Ж", u"ZH"),
        #(u"Ж", u"GH"),
        (u"Ц", u"TS"),
        (u"Ч", u"CH"),
        (u"Ш", u"SH"),
        (u"Ы", u"YI"),
        #(u"Ы", u"Y"),
        (u"Ю", u"YU"),
        (u"Я", u"YA"),
        # one-symbol
        (u"А", u"A"),
        (u"Б", u"B"),
        (u"В", u"V"),
        (u"Г", u"G"),
        (u"Д", u"D"),
        (u"Е", u"E"),
        (u"З", u"Z"),
        (u"И", u"I"),
        (u"Й", u"J"),
        (u"К", u"K"),
        (u"Л", u"L"),
        (u"М", u"M"),
        (u"Н", u"N"),
        (u"О", u"O"),
        (u"П", u"P"),
        (u"Р", u"R"),
        (u"С", u"S"),
        (u"Т", u"T"),
        (u"У", u"U"),
        (u"Ф", u"F"),
        (u"Х", u"H"),
        (u"Э", u"E"),
        (u"Ъ", u"`"),
        (u"Ь", u"'"),
        ## Маленькие буквы
        # three-symbols
        (u"щ", u"sch"),
        # two-symbols
        (u"ё", u"yo"),
        (u"ж", u"zh"),
        #(u"ж", u"gh"),
        (u"ц", u"ts"),
        (u"ч", u"ch"),
        (u"ш", u"sh"),
        (u"ы", u"yi"),
        #(u"ы", u"y"),
        (u"ю", u"yu"),
        (u"я", u"ya"),
        # one-symbol
        (u"а", u"a"),
        (u"б", u"b"),
        (u"в", u"v"),
        (u"г", u"g"),
        (u"д", u"d"),
        (u"е", u"e"),
        (u"з", u"z"),
        (u"и", u"i"),
        (u"й", u"j"),
        (u"к", u"k"),
        (u"л", u"l"),
        (u"м", u"m"),
        (u"н", u"n"),
        (u"о", u"o"),
        (u"п", u"p"),
        (u"р", u"r"),
        (u"с", u"s"),
        (u"т", u"t"),
        (u"у", u"u"),
        (u"ф", u"f"),
        (u"х", u"h"),
        (u"э", u"e"),
        ## Символы
        (u'№', u'N'),
        (u"ъ", u"`"),
        (u"ь", u"'"),
    )
    # перебираем символы в таблице и заменяем
    for symb_in, symb_out in transtable:
        name = name.replace(symb_in, symb_out)
    # возвращаем переменную
    return name

# Известные альтернативные написания транслитерации
# Формат: {латинское_написание: [альтернативы]}
translit_alternatives = {
    'yi': ['y', 'i', 'ij', 'yi', 'j', 'iy'],
    'iy': ['y', 'i', 'ij', 'yi', 'j', 'iy'],
    'j': ['y', 'i', 'ij', 'yi', 'j', 'iy'],
    'y': ['yi', 'i', 'ij', 'yy', 'y'],
    'i': ['y', 'yi', 'i'],
    'ii': ['y', 'yi', 'ii'],
    'yy': ['y', 'yi', 'i', 'yy'],
    'e': ['ye', 'eh', 'e'],
    'yo': ['e', 'io', 'yo'],
    'ye': ['yo', 'e', 'ie', 'ye'],
    'zh': ['j', 'gh', 'zh'],
    'gh': ['j', 'zh', 'gh'],
    'kh': ['h', 'ch', 'kh'],
    'ts': ['c', 'ts'],
    'ch': ['tch', 'ch'],
    'sh': ['sch', 'sh'],
    'shch': ['sch', 'shch'],
    'sch': ['sh', 'shch', 'sch'],
    'yu': ['u', 'yu', 'iu', 'ju'],
    'ya': ['a', 'ya', 'ia', 'ja'],
    '`': ['', 'y', '`'],
    "'": ['', 'y', "'"],
}

def generate_latin_variants(text):
    """Генерирует варианты написания с учетом альтернативной транслитерации"""
    if not text:
        return ['']

    variants = set()
    text_lower = text.lower()

    def backtrack(start, current):
        if start == len(text_lower):
            variants.add(current)
            return

        # Пробуем найти самое длинное совпадение с альтернативами
        found = False
        for length in range(min(4, len(text_lower) - start), 0, -1):
            substr = text_lower[start:start + length]
            if substr in translit_alternatives:
                # Используем оригинальный регистр
                original_substr = text[start:start + length]
                for alt in translit_alternatives[substr]:
                    # Сохраняем регистр первой буквы
                    if original_substr[0].isupper() and len(alt) > 0:
                        alt = alt[0].upper() + alt[1:]
                    backtrack(start + length, current + alt)
                found = True

        # Если не нашли альтернативу, оставляем как есть
        if not found:
            backtrack(start + 1, current + text[start])

    backtrack(0, '')
    variants.add(text)
    return list(variants)


if __name__ == "__main__":
    trans = translate('белоусовы тех паспорт жил помещ_2026-03-03_11-19-39_1')
    etalon = 'belousovy_teh_pasport_ghil_pomesch_2026-03-03_11-19-39_1'
    print(etalon,'=', trans, generate_latin_variants(trans))
