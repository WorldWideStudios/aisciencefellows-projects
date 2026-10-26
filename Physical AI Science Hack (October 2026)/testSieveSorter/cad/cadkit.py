"""Shared export step for every part: STEP + STL + shaded PNG preview + checks JSON."""
from pathlib import Path
import json
from cadquery import exporters
import trimesh
import vtk

OUT = Path(__file__).resolve().parent / "out"
BED = (220.0, 220.0, 250.0)  # printer build volume, mm


def render(stl, png, elev=35, azim=-30):
    """Offscreen VTK render of the STL (VTK ships with CadQuery)."""
    reader = vtk.vtkSTLReader()
    reader.SetFileName(str(stl))
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(reader.GetOutputPort())
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(0.62, 0.70, 0.78)
    ren = vtk.vtkRenderer()
    ren.AddActor(actor)
    ren.SetBackground(1, 1, 1)
    cam = ren.GetActiveCamera()
    cam.SetViewUp(0, 0, 1)
    cam.SetPosition(0, -1, 0)
    ren.ResetCamera()
    cam.Azimuth(azim)
    cam.Elevation(elev)
    cam.OrthogonalizeViewUp()
    ren.ResetCamera()
    win = vtk.vtkRenderWindow()
    win.SetOffScreenRendering(1)
    win.AddRenderer(ren)
    win.SetSize(900, 700)
    win.Render()
    grab = vtk.vtkWindowToImageFilter()
    grab.SetInput(win)
    writer = vtk.vtkPNGWriter()
    writer.SetFileName(str(png))
    writer.SetInputConnection(grab.GetOutputPort())
    writer.Write()


def export_all(part, name, extra=None):
    """Write out/<name>.step/.stl/.png and out/<name>_checks.json; return the checks."""
    OUT.mkdir(exist_ok=True)
    solid = part.val()
    exporters.export(part, str(OUT / f"{name}.step"))
    exporters.export(part, str(OUT / f"{name}.stl"), tolerance=0.04, angularTolerance=0.1)
    render(OUT / f"{name}.stl", OUT / f"{name}.png")
    mesh = trimesh.load_mesh(OUT / f"{name}.stl")
    bb = solid.BoundingBox()
    size = (bb.xlen, bb.ylen, bb.zlen)
    checks = {
        "valid_solid": solid.isValid(),
        "single_solid": len(part.solids().vals()) == 1,
        "watertight_mesh": bool(mesh.is_watertight),
        "bbox_mm": [round(v, 2) for v in size],
        "fits_bed": all(s <= b for s, b in zip(size, BED)),
        "volume_cm3": round(solid.Volume() / 1000, 2),
        **(extra or {}),
    }
    (OUT / f"{name}_checks.json").write_text(json.dumps(checks, indent=2))
    return checks
