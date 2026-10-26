from pathlib import Path
import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
import json, math
root=Path(__file__).resolve().parent
s=cq.importers.importStep(str(root/'reference/Wrist_Roll_Follower_SO101.step')).val()
h=[]
for f in s.Faces():
 if f.geomType()!='CYLINDER':continue
 c=BRepAdaptor_Surface(f.wrapped).Cylinder();p=c.Location();d=c.Axis().Direction();b=f.BoundingBox()
 if abs(c.Radius()-1.6)<1e-5 and abs(d.Z())>.999 and b.zmin<2:
  h.append({'x':p.X(),'y':p.Y(),'radius':c.Radius(),'z_min':b.zmin,'z_max':b.zmax})
cx=sum(a['x'] for a in h)/len(h);cy=sum(a['y'] for a in h)/len(h)
r=[math.hypot(a['x']-cx,a['y']-cy) for a in h]
report={'source_holes':h,'source_axis_center_xy':[cx,cy], 'bolt_circle_diameter':sum(r)*2/len(r),'square_spacing':max(a['x'] for a in h)-min(a['x'] for a in h),'bearing_web_thickness':h[0]['z_max']-h[0]['z_min']}
assert len(h)==4
(root/'reference/measurements.json').write_text(json.dumps(report,indent=2))
print(report)
