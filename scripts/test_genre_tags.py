from src.tools.semantic_search_tool import _derive_explanation_fields

genres = ["Rock", "International", "Country", "Soul-RnB", "Easy Listening"]
for g in genres:
    r = _derive_explanation_fields(g)
    has_mood = "mood_tags" in r
    has_scene = "scene_tags" in r
    print(g + ": mood=" + str(has_mood) + ", scene=" + str(has_scene))
