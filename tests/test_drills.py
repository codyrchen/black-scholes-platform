import math

import pytest

from quant.drills import CATEGORIES, DIFFICULTIES, GENERATORS, generate_round, make_question, question_from_id

SEEDS = range(150)


@pytest.mark.parametrize("name", sorted(GENERATORS))
def test_every_question_accepts_its_own_answer(name):
    for seed in SEEDS:
        q = make_question(name, seed)
        assert q.category in CATEGORIES and q.difficulty in DIFFICULTIES
        assert q.is_correct(q.answer), q
        if q.choices is not None:
            assert 0 <= q.answer < len(q.choices)
            assert len(set(q.choices)) == len(q.choices)
        else:
            assert math.isfinite(q.answer)


@pytest.mark.parametrize("name", sorted(n for n, g in GENERATORS.items() if g.category == "mental_math"))
def test_mental_math_shortcut_is_accepted(name):
    """The rule of thumb in each explanation must land within the stated tolerance."""
    for seed in SEEDS:
        q = make_question(name, seed)
        if q.shortcut is not None:
            assert q.is_correct(q.shortcut), (q.prompt, q.shortcut, q.answer)


def test_questions_are_deterministic_and_round_trip_through_id():
    for name in GENERATORS:
        a = make_question(name, 12345)
        b = question_from_id(a.id)
        assert a == b


def test_wrong_answers_are_rejected():
    q = make_question("put_call_parity", 1)
    assert not q.is_correct(q.answer + 1.0)
    assert not q.is_correct("not a number")
    assert not q.is_correct(float("nan"))
    c = make_question("greek_sign", 1)
    assert not c.is_correct(1 - int(c.answer))


def test_public_view_hides_the_answer():
    for name in GENERATORS:
        pub = make_question(name, 3).public()
        assert "answer" not in pub and "explanation" not in pub


@pytest.mark.parametrize("name", ["parity_arb", "vertical_arb", "butterfly_arb", "greek_sign"])
def test_choice_questions_cover_every_answer(name):
    answers = {make_question(name, s).answer for s in SEEDS}
    expected = set(range(len(make_question(name, 0).choices)))
    assert answers == expected


def test_parity_arbitrage_labels_match_the_quotes():
    for seed in SEEDS:
        q = make_question("parity_arb", seed)
        assert q.answer in (0, 1, 2)


def test_round_filters():
    qs = generate_round(20, seed=1, categories=["arbitrage"], difficulties=["hard"])
    assert {q.id.rsplit("-", 1)[0] for q in qs} == {"butterfly_arb"}
    assert generate_round(5, seed=9) == generate_round(5, seed=9)
    with pytest.raises(ValueError):
        generate_round(5, categories=["pricing"], difficulties=["easy"])


@pytest.mark.parametrize("bad", ["", "nope-1", "atm_call-abc", "atm_call--5", "atm_call-99999999999"])
def test_bad_ids_raise(bad):
    with pytest.raises((KeyError, ValueError)):
        question_from_id(bad)
