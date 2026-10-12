from antar_engine import display_names as DN


def test_full_names_become_first_names_everywhere():
    d = {"name_a": "Raman Singh", "name_b": "Andres Botero", "summary": "Read as a counsel fit, Andres Botero sees things differently from Raman Singh.",
         "layers": [{"detail": "You and Andres Botero don't always hear each other."}], "n": 3}
    out = DN.apply(d, ["Raman Singh", "Andres Botero"])
    assert out["summary"] == "Read as a counsel fit, Andres sees things differently from Raman." and out["layers"][0]["detail"] == "You and Andres don't always hear each other."
    assert out["name_a"] == "Raman" and out["name_b"] == "Andres" and out["n"] == 3


def test_single_names_and_shared_first_names_are_left_alone():
    assert DN.apply("saransh and Raman", ["Raman", "saransh"]) == "saransh and Raman"
    assert DN.apply("Raman Singh and Raman Patel", ["Raman Singh", "Raman Patel"]) == "Raman Singh and Raman Patel"    # ambiguous: keep full
    assert DN.apply("Anne Marie Lee and Joe", ["Anne Marie Lee", "Joe"]) == "Anne and Joe"
    assert DN.apply({"x": None, "y": [1]}, ["A B", "C"]) == {"x": None, "y": [1]}                                       # never raises on odd shapes
    assert DN.apply("Rajeev Singhania", ["Raj Singh", "Sam"]) == "Rajeev Singhania"                                      # whole-word match only
