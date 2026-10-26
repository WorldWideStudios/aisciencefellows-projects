"""Tests for per-column concoction orders: rules, tip budget and the generated protocol."""

import io

import pytest
from opentrons.simulate import simulate

from concoction import Ingredient, Recipe, order_summary, protocol_source, validate_order


def order():
    return [
        Recipe(1, [Ingredient(1, 40), Ingredient(3, 10)], "Cisplatin in saline"),
        Recipe(2, [Ingredient(2, 120), Ingredient(1, 30), Ingredient(4, 5)], "Doxorubicin in D5W"),
    ]


def run_log(text):
    log, _ = simulate(io.StringIO(text), "concoction.py")
    return [entry["payload"]["text"] for entry in log]


def test_valid_order_has_no_problems():
    assert validate_order(order()) == []


@pytest.mark.parametrize("recipes, problem", [
    ([Recipe(1, [Ingredient(1, 150), Ingredient(2, 60)])], "column 1: 210 µL is more than a well holds (200 µL)"),
    ([Recipe(1, [Ingredient(1, 4)])], "column 1: 4 µL from trough 1 is below the 5 µL minimum"),
    ([Recipe(13, [Ingredient(1, 10)])], "column 13 doesn't exist (1-12)"),
    ([Recipe(1, [Ingredient(13, 10)])], "column 1: trough 13 doesn't exist (1-12)"),
    ([Recipe(1, [])], "column 1 has no ingredients"),
    ([Recipe(1, [Ingredient(1, float("nan"))])], "column 1: nan µL from trough 1 is not a volume"),
    ([Recipe(1, [Ingredient(1, 10)]), Recipe(1, [Ingredient(2, 10)])], "column 1 is ordered twice"),
])
def test_rule_violations(recipes, problem):
    assert problem in validate_order(recipes)


def test_used_columns_and_trough_volume_are_checked():
    problems = validate_order(order(), used_columns={2}, trough_volumes_ul={1: 500})
    assert "column 2 already holds a concoction" in problems
    # trough 1 is drawn by 8 channels: 8 x (40 + 30) = 560 µL
    assert "trough 1 needs 560 µL but holds 500 µL" in problems


def test_tip_budget():
    many_small = [Recipe(c, [Ingredient(1, 10), Ingredient(2, 10)]) for c in range(1, 8)]  # 14 small draws
    assert "needs 14 columns of 50 µL tips but 12 are left" in validate_order(many_small)
    assert "needs 2 columns of 50 µL tips but 1 are left" in validate_order(
        [Recipe(1, [Ingredient(1, 10), Ingredient(2, 10)])], small_tips_left=1)


def test_summary_counts_tips_and_trough_draws():
    summary = order_summary(order())
    assert summary["small_tips"] == 4 and summary["large_tips"] == 1
    assert summary["trough_draw_ul"] == {1: 560.0, 2: 960.0, 3: 80.0, 4: 40.0}
    assert summary["column_totals"] == {1: 50.0, 2: 155.0}


def test_protocol_simulates_with_fresh_tip_per_draw_and_mix():
    lines = run_log(protocol_source(order(), small_tip_start=1, large_tip_start=1))
    pickups = [l for l in lines if l.startswith("Picking up tip")]
    assert len(pickups) == 5  # one per reservoir draw, never reused
    assert pickups[0].startswith("Picking up tip from A1 of Opentrons Flex 96 Filter Tip Rack 50 µL")
    assert any("Tip Rack 1000 µL on slot A1" in p for p in pickups)  # 120 µL draw uses a 1000 µL tip
    assert sum(l.startswith("Dropping tip") for l in lines) == 5
    assert "Aspirating 120.0 uL from A2 of NEST 12 Well Reservoir 15 mL on slot B1" in "\n".join(lines)
    assert "Dispensing 120.0 uL into A2 of Armadillo 96 Well Plate 200 µL PCR Full Skirt on slot B3" in "\n".join(lines)
    assert sum(l.startswith("Mixing") for l in lines) == 2  # last ingredient of each column mixes


def test_tip_columns_continue_from_start():
    lines = run_log(protocol_source(order(), small_tip_start=5, large_tip_start=3))
    pickups = [l for l in lines if l.startswith("Picking up tip")]
    assert pickups[0].startswith("Picking up tip from A5 of Opentrons Flex 96 Filter Tip Rack 50 µL")
    assert any(p.startswith("Picking up tip from A3 of Opentrons Flex 96 Tip Rack 1000 µL") for p in pickups)


def test_invalid_order_refuses_to_generate():
    with pytest.raises(ValueError, match="more than a well holds"):
        protocol_source([Recipe(1, [Ingredient(1, 150), Ingredient(2, 60)])])


def test_recipe_names_cannot_inject_code():
    import ast

    recipes = [Recipe(1, [Ingredient(1, 10)], 'x"""\nimport os\n"""')]
    tree = ast.parse(protocol_source(recipes))
    imports = [ast.unparse(n) for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert imports == []
