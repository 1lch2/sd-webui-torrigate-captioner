from .prompts import make_user_query

def _empty_grounding():
    return {
        "tags": [],
        "characters": [],
        "char_p_tags": {"chars": {}, "skins": {}},
        "char_descr": {"chars": {}, "skins": {}},
    }

def _split_csv(value):
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]

def build_grounding(
    caption_type="short",
    use_names=True,
    add_tags=False,
    tags="",
    add_character_list=False,
    character_names="",
    character_count=1,
    add_character_tags=False,
    add_character_descriptions=False,
    char1_name="",
    char1_tags="",
    char2_name="",
    char2_tags="",
    char3_name="",
    char3_tags="",
    char4_name="",
    char4_tags="",
    char5_name="",
    char5_tags="",
    char1_description="",
    char2_description="",
    char3_description="",
    char4_description="",
    char5_description="",
):
    item = _empty_grounding()
    if add_tags:
        item["tags"] = _split_csv(tags)
    if add_character_list:
        item["characters"] = _split_csv(character_names)

    char_entries = [
        (char1_name, char1_tags if add_character_tags else "", char1_description if add_character_descriptions else ""),
        (char2_name, char2_tags if add_character_tags else "", char2_description if add_character_descriptions else ""),
        (char3_name, char3_tags if add_character_tags else "", char3_description if add_character_descriptions else ""),
        (char4_name, char4_tags if add_character_tags else "", char4_description if add_character_descriptions else ""),
        (char5_name, char5_tags if add_character_tags else "", char5_description if add_character_descriptions else ""),
    ][:int(character_count)]

    auto_chars = []
    for index, (raw_name, raw_tags, raw_description) in enumerate(char_entries):
        name = raw_name.strip() if raw_name else ""
        if not name and index < len(item["characters"]):
            name = item["characters"][index]
        if not name:
            continue

        auto_chars.append(name)

        parsed_tags = _split_csv(raw_tags)
        if parsed_tags:
            item["char_p_tags"]["chars"][name] = parsed_tags

        description = raw_description.strip() if raw_description else ""
        if description:
            item["char_descr"]["chars"][name] = description

    if auto_chars and not item["characters"]:
        item["characters"] = auto_chars

    prompt = make_user_query(
        item,
        c_type=caption_type,
        use_names=use_names,
        add_tags=add_tags,
        add_characters=add_character_list,
        add_char_tags=add_character_tags,
        add_description=add_character_descriptions,
        underscores_replace=False,
    )

    return prompt
