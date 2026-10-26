from baebugs.insect_kg import (
    break_point,
    insect_tree,
    observe,
    rebuild_hash,
    strip,
    verify_tree,
)
from baebugs.insect_lomo import check, family_stats, novelty_logic
from baebugs.printmodels import toy_fields


def test_insect_hash_deterministic_and_tamper_evident():
    a_nodes, a = insect_tree(13.5, "bee")
    assert rebuild_hash(13.5, "bee") == a["hash"]
    nodes = [strip(n) for n in a_nodes]
    assert verify_tree(nodes) == (True, None)
    nodes[3]["bbox"][1][0] += 0.01
    assert verify_tree(nodes)[0] is False


def test_break_point_and_topology():
    a, ra = insect_tree(13.5, "bee"); b, rb = insect_tree(13.6, "bee"); _c, rc = insect_tree(13.5, "wasp")
    assert break_point(a, b)["level"] == 0 and ra["topo"] == rb["topo"] and ra["topo"] != rc["topo"]


def test_levels_and_checks():
    nodes, root = insect_tree(13.5, "bee")
    assert {n["level"] for n in nodes} == {0, 1, 2, 3} and root["ok"]
    assert root["counts"] == {"legs": 6, "antennae": 2, "wings": 2}
    _, tiny = insect_tree(1.0, "thrips")
    assert not tiny["ok"]                       # fuse_minimum break point on a 1 mm toy


def test_toy_roles():
    assert toy_fields("Apidae", "CA museum", 13.5)["training_role"] == "positive"
    assert toy_fields("Halictidae", "CA museum", 9.9)["training_role"] == "edge_negative:family_stats_suspect"
    assert toy_fields("Apidae (Bombus mixtus)", "outside CA", 28.2)["training_role"] == "edge_negative:size_suspect"
    assert toy_fields("thrips-like", "fill-in: x", 1.0)["training_role"] == "edge_negative:below_database"
    assert toy_fields("Apidae", "CA museum", 13.5)["representation"] == "toy"


def test_observation_check_and_scoring():
    _, r = insect_tree(13.5, "bee")
    held = {"name": "x", "group": "california", "family_base": "Apidae", "length_mm": 13.5, "plan": "bee",
            "insect_hash": r["hash"], "topo_hash": r["topo"], "kit_tray": r["kit_tray"], "observation": observe(r),
            "order": "Hymenoptera"}
    ctx = [dict(held, name="y", length_mm=17.1)]
    good = check({"family": "Apidae", "plan": "bee", "length_mm": 13.5, "novel": False}, held, ctx)
    bad = check({"family": "Apidae", "plan": "wasp", "length_mm": 13.5}, held, ctx)
    assert good["hash_match"] and good["obs_consistent"] and good["triage_ok"]
    assert not bad["hash_match"] and bad["break_point"].startswith("L3 topology")
    assert novelty_logic("Apidae", 2.0, family_stats(ctx))[0]       # below database minimum
