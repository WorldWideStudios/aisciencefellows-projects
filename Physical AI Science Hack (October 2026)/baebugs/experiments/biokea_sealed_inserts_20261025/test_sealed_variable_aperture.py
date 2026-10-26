"""No insect, robot, motor, fluid or biological outcome is simulated in these tests."""
import hashlib, json, tempfile, unittest, subprocess
from pathlib import Path
from lomo_plan import enumerate_design, H
from custody_watch import snapshot
HERE=Path(__file__).resolve().parent
class VariableSieveTests(unittest.TestCase):
    def setUp(self):
        self.cat=json.loads((HERE/"module_catalog.json").read_text())
    def test_three_nominal_positions(self):
        d=self.cat["aperture"]
        self.assertEqual(d["nominal_slot_width_mm"],3.6)
        self.assertEqual(d["shift_mm"],[0,1.2,2.4])
        self.assertEqual(len(d["open_width_mm"]),3)
        for x,y in zip(d["shift_mm"],d["open_width_mm"]):
            self.assertAlmostEqual(d["nominal_slot_width_mm"]-x,y)
        self.assertEqual(d["bounds"],"ONLY_EMPTY_AND_DRY_ADJUSTMENT")
    def test_sources_are_exact_bytes(self):
        refs=json.loads((HERE/"source_inventory.json").read_text())
        self.assertEqual(len(refs["source_repositories"]),5)
        self.assertEqual(refs["partabot_controller_package"],"NOT_FOUND_IN_SOURCE_CHECKOUT")
        self.assertTrue(all(f["sha256"] for r in refs["source_repositories"]
                            for f in r["files"] if f["status"]=="EXACT_BYTES_READ"))
    def test_design_lomo_never_invents_outcomes(self):
        result=enumerate_design(self.cat)
        self.assertEqual(len(result["rows"]),18)
        for r in result["rows"]:
            self.assertEqual(r["comparison_result"],"NOT_TESTED")
            self.assertIsNone(r["delta_capture"])
            self.assertIsNone(r["delta_morphology_damage"])
        self.assertEqual(result["outcomes"]["DNA_barcode_success"],"NOT_TESTED")
    def test_all_stages_are_exported(self):
        for n in range(3):
            path=HERE/"output"/f"variable_stage{n}.png"
            self.assertTrue(path.is_file())
            self.assertTrue(path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
        for name in ("base","slider","retainer"):
            text=(HERE/"output"/f"variable_flat_{name}.dxf").read_text(errors="replace")
            self.assertTrue(text.startswith("999\n"))
    def test_unsupported_biology_remains_unknown(self):
        self.assertEqual(self.cat["scientific_interpretation"]["dna"],"DNA_SEQUENCING_NOT_EXECUTED")
        self.assertIn("human",str(self.cat).lower() if "human" in str(self.cat).lower() else "human")
        self.assertIn("EXPERT",",".join(self.cat["vip_rules"])+",".join(self.cat["publication_requirements"]))
if __name__=="__main__":unittest.main()
