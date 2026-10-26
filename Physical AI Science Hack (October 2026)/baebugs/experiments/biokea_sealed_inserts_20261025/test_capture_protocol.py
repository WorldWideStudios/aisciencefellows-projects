"""Pure software regression cases. Tests do NOT capture real insects or run hardware."""
import argparse
import tempfile
import unittest
from pathlib import Path
import capture_receipt as C

IMAGE = C.EXPERIMENT/"output"/"round_insert_closeup.png"

def args(**changes):
    d=dict(image=str(IMAGE),stage="INTAKE",sample_id="FIXTURE_ONLY",
           fraction_id="F0",tray_id="TRAY-UNMEASURED",insert_id="SS-RND-CONCEPT",
           gasket_lot="NOT_ASSIGNED",camera_id="MANUAL_FILE_IMPORT",
           calibration_id="UNVERIFIED",operator_id="software_test",
           frame_id="TEST-IMAGE-OCC-01",observed_count=None,flag=None,notes="")
    d.update(changes)
    return argparse.Namespace(**d)

class CaptureTests(unittest.TestCase):
    def test_exact_bytes_and_same_content_different_context(self):
        with tempfile.TemporaryDirectory() as d:
            x=C.ingest(args(),store=d,append=lambda rec:rec)
            y=C.ingest(args(frame_id="TEST-IMAGE-OCC-02"),store=d,append=lambda rec:rec)
            self.assertEqual(x["image_sha256"],y["image_sha256"])
            self.assertNotEqual(x["capture_atom_content_sha256"],y["capture_atom_content_sha256"])
            self.assertEqual(len(list(Path(d).glob("*.png"))),1)
            self.assertEqual(x["organism_identity"],"UNKNOWN")
            self.assertFalse(x["downstream_auto_admit"])
    def test_invalid_label_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                C.ingest(args(flag="TAMPER_SNEAK"),store=d,append=lambda rec:rec)
            with self.assertRaises(ValueError):
                C.ingest(args(gasket_lot=""),store=d,append=lambda rec:rec)
            with self.assertRaises(ValueError):
                C.ingest(args(observed_count=-1),store=d,append=lambda rec:rec)
    def test_preexisting_tamper_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            C.ingest(args(),store=d,append=lambda rec:rec)
            file=next(Path(d).glob("*.png"))
            file.write_bytes(file.read_bytes()+b"TAMPER")
            with self.assertRaisesRegex(ValueError,"modified"):
                C.ingest(args(frame_id="TEST-IMAGE-OCC-03"),store=d,append=lambda rec:rec)
    def test_fault_requires_review(self):
        with tempfile.TemporaryDirectory() as d:
            x=C.ingest(args(stage="EDGE_INSPECTION",flag="GASKET_PINCHED"),
                       store=d,append=lambda rec:rec)
            self.assertEqual(x["fault"],"GASKET_PINCHED")
            self.assertFalse(x["downstream_auto_admit"])

if __name__=="__main__":unittest.main(verbosity=2)
