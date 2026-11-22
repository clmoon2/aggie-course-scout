import math

from query import load_index, parse_query, search


def tiny_index():
    docs = [
        ["u:A-100", "A 100", "Database Systems", "A", "Computing", "College", "undergraduate", "3", "u", "computing", 3, 3],
        ["u:A-200", "A 200", "Operating Systems", "A", "Computing", "College", "undergraduate", "3", "u", "computing", 3, 3],
        ["u:B-300", "B 300", "Organic Chemistry", "B", "Chemistry", "College", "undergraduate", "4", "u", "chemistry", 4, 4],
    ]
    terms = {"databas": {"t": [[0, 1]], "x": [[0, 2]], "d": [], "p": []},
             "system": {"t": [[1, 1]], "x": [[1, 2], [0, 1]], "d": [], "p": []},
             "chemistri": {"t": [[2, 0]], "x": [[2, 3]], "d": [], "p": []}}
    return {
        "n": 3, "k1": 1.2, "b": 0.75, "terms": terms,
        "weights": {"t": 3.0, "d": 2.0, "x": 1.0, "p": 0.5},
        "avglen": {"t": 1.0, "d": 1.0, "x": 2.0, "p": 1.0},
        "doclen": {"t": [1, 1, 1], "d": [1, 1, 1], "x": [2, 2, 2], "p": [1, 1, 1]},
        "docs": docs, "text": [["database systems", "", "Database Systems"],
                               ["operating systems", "", "Operating Systems"],
                               ["chemistry", "", "Organic Chemistry"]],
    }


def test_bm25f_math_matches_hand_calculation():
    idx = tiny_index()
    res = search(idx, "database", 3, explain=True)
    # df=1, N=3: idf=ln(1+2.5/1.5); title norm=3, saturates to 3*2.2/(1.2+3).
    idf = math.log(1 + 2.5 / 1.5)
    expected = idf * 5 * 2.2 / 6.2
    assert abs(res["results"][0]["score"] - expected) < 0.01
    assert res["results"][0]["why"]["databas"]["fields"]["t"]["tf"] == 1


def test_title_weight_beats_description():
    idx = tiny_index()
    res = search(idx, "system", 5)
    assert res["results"][0]["code"] == "A 200"


def test_phrase_requires_adjacency():
    idx = tiny_index()
    assert search(idx, '"database systems"', 5)["total"] == 1
    assert search(idx, '"systems database"', 5)["total"] == 0


def test_parser_quotes_and_filters():
    idx = tiny_index()
    q = parse_query('dept:a "operating systems" -level:graduate credits:>=3', idx)
    assert q.phrases == [["oper", "system"]]
    assert q.depts == ["A"]
    assert q.neg_levels == ["graduate"]
    assert q.credits == (">=", 3)


def test_filters_exclude():
    idx = tiny_index()
    assert search(idx, "systems dept:b", 5)["total"] == 0
    assert search(idx, "systems credits:>=4", 5)["total"] == 0


def test_negation_excludes():
    idx = tiny_index()
    assert search(idx, "systems -dept:a", 5)["total"] == 0
    assert search(idx, "systems -database", 5)["total"] == 1


def test_filter_only_query_works():
    idx = tiny_index()
    res = search(idx, "credits:4", 5)
    assert res["total"] == 1
    assert res["results"][0]["code"] == "B 300"


def test_suggestion_and_correction():
    idx = load_index()
    q = parse_query("databse", idx)
    assert q.corrections.get("databs") == "database"
    res = search(idx, "databse", 5)
    assert res["total"] > 0
    assert "database" in res["results"][0]["title"].lower()


def test_college_filter():
    idx = tiny_index()
    res = search(idx, "systems college:computing", 5)
    assert res["total"] == 2
    assert all(r["college"] == "College" for r in res["results"])


def test_credit_bucket_facets_match_filter_results():
    idx = tiny_index()
    res = search(idx, "", 20)
    for bucket, count in res["facets"]["credits"].items():
        assert search(idx, f"credits:{bucket}", 20)["total"] == count


def test_credit_operator_compares_both_bounds():
    idx = tiny_index()
    assert search(idx, "credits:<=3", 20)["total"] == 2
    assert search(idx, "credits:>=4", 20)["total"] == 1


def test_singular_summary_value_is_two_courses():
    idx = tiny_index()
    res = search(idx, "database", 20)
    assert res["total"] == 1
