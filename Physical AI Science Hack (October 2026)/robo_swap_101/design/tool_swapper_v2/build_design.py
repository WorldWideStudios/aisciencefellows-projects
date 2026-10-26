"""Three-stud keyhole twist coupling. mm, z insertion, y vertical at entry."""
from pathlib import Path
import math,json
import cadquery as cq
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'cad';OUT.mkdir(exist_ok=True)
V=cq.Vector
TURN=45; DRAW=.8; R=15; CLEAR=.25
P=dict(twist_degrees=TURN,draw_in_mm=DRAW,dowel_count=3,dowel_circle_diameter_mm=30,dowel_stem_diameter_mm=3.6,dowel_head_diameter_mm=6,dowel_projection_mm=8,head_thickness_mm=1.8,flare_start_mm=5.2,head_start_mm=6.2,central_vertical_key_mm=[3,10,8],key_head_start_mm=3.4,key_entry_y_mm=[-4,6],key_neck_diameter_mm=3,key_clearance_entry_mm=.35,key_clearance_seated_mm=.06,entry_lip_depth_mm=2.1,male_flange_mm=[40,7],female_body_mm=[44,44,18],tool_blank_mm=[24,24,18],mount_bolt_circle_mm=14,mount_hole_mm=3.2,clearance_per_side_mm=CLEAR,pin_lock=False)
def cyl(r,h,x=0,y=0,z=0):return cq.Solid.makeCylinder(r,h,V(x,y,z))
def box(x,y,z,c):return cq.Workplane('XY').box(x,y,z).translate(c).val()
def pose(s,a,offset=0):return s.rotate((0,0,0),(0,0,1),a).translate((0,0,offset))
def xy(a):return R*math.cos(math.radians(a)),R*math.sin(math.radians(a))
# Preserve original horn mounting and 3 mm screw-bearing web.
male=cyl(20,7,z=-7).cut(cyl(10,1.001,z=-7.001)).cut(cyl(2.7,4.001,z=-7.001))
h=7/math.sqrt(2)
for x in [-h,h]:
 for y in [-h,h]:male=male.cut(cyl(1.6,7.02,x,y,-7.01)).cut(cyl(3.1,3.01,x,y,-3))
# Asymmetric vertical head enters only one way; the narrow round neck
# rotates within the front lip after the head passes behind it.
key=box(3,10,4.6,(0,1,5.7))
key=cq.Workplane(obj=key).edges('>Z').chamfer(.3).val()
male=male.fuse(cyl(1.5,3.5)).fuse(key)
phases=[90,210,330]
for a in phases:
 x,y=xy(a)
 stud=cyl(1.8,5.2,x,y).fuse(cq.Solid.makeCone(1.8,3,1,V(x,y,5.2))).fuse(cyl(3,1.8,x,y,6.2))
 male=male.fuse(stud)
male=male.clean()
female=box(44,44,18,(0,0,9)).fuse(box(24,24,18,(0,0,27)))
# Swept, flared-head pockets behind narrower curved neck slots. Each pocket
# rises .8 mm over 45 degrees: head underside bears on the ramp when pulled.
# Loft radial pocket sections along the rising circular path.
def swept_profile(phase,profile):
 wires=[]
 for i in range(31):
  a=TURN*i/30;t=math.radians(phase+a);dz=-DRAW+DRAW*a/TURN
  wires.append(cq.Wire.makePolygon([V((R+dr)*math.cos(t),(R+dr)*math.sin(t),z+dz) for dr,z in profile],close=True))
 return cq.Solid.makeLoft(wires,False)
for phase in phases:
 x,y=xy(phase)
 female=female.cut(cyl(3.3,8.4,x,y,-.01))
 profile=[(-2.05,-1.1),(2.05,-1.1),(2.05,4.95),(3.25,5.95),(3.25,8.25),(-3.25,8.25),(-3.25,5.95),(-2.05,4.95)]
 female=female.cut(swept_profile(phase,profile))
 # Round end caps capture the circular heads at the two ends of the arc.
 for a in [0,TURN]:
  xx,yy=xy(phase+a);dz=-DRAW+DRAW*a/TURN
  female=female.cut(cyl(2.05,6.25+dz,xx,yy,-.01),cq.Solid.makeCone(2.05,3.25,1,V(xx,yy,4.95+dz)),cyl(3.25,2.3,xx,yy,5.95+dz))
# A single vertical entry gate, asymmetric top/bottom, in a 2.1 mm lip.
# Behind the lip a swept fan allows the head to turn. Clearance decreases
# gradually along the path; the three stud ramps supply axial draw-in.
from shapely.geometry import Polygon
from shapely.ops import unary_union
profiles=[]
for i in range(181):
 a=TURN*i/180;t=math.radians(a);c=.35-(.35-.06)*a/TURN
 pts=[(-1.5-c,-4-c),(1.5+c,-4-c),(1.5+c,6+c),(-1.5-c,6+c)]
 profiles.append(Polygon([(x*math.cos(t)-y*math.sin(t),x*math.sin(t)+y*math.cos(t)) for x,y in pts]))
fan=unary_union(profiles)
opening=cq.Workplane('XY').polyline(list(fan.exterior.coords)[:-1]).close().extrude(6.4).translate((0,0,2.1)).val()
entry=box(3.7,10.7,8.6,(0,1,4.15))
female=female.cut(opening).cut(entry).cut(cyl(1.7,3.5,z=-.01)).clean()
parts={'male':male,'female':female}
for n,s in parts.items():
 assert s.isValid() and len(s.Solids())==1,n
 cq.exporters.export(s,str(OUT/(n+'.step')))
 cq.exporters.export(s,str(OUT/(n+'.stl')),tolerance=.035,angularTolerance=.08)
seated=pose(male,TURN)
assy=cq.Assembly(name='SO101_keyhole_v2')
assy.add(seated,name='male',color=cq.Color(.12,.44,.72));assy.add(female,name='female',color=cq.Color(.87,.51,.15));assy.export(str(OUT/'assembled.step'))
checks=[]
for i in range(19):
 a=TURN*i/18;offset=-DRAW+DRAW*a/TURN
 vol=pose(male,a,offset).intersect(female).Volume()
 checks.append(dict(angle_deg=a,axial_offset_mm=offset,interference_mm3=vol));assert vol<.01,checks[-1]
for offset in [-9,-7,-5,-3,-.8]:
 vol=pose(male,0,offset).intersect(female).Volume()
 checks.append(dict(insertion_offset_mm=offset,interference_mm3=vol));assert vol<.01,checks[-1]
orientation_checks=[]
for a in [90,120,180,240,270]:
 # Head crossing the entry lip, before reaching the internal turning chamber.
 vol=pose(male,a,-6).intersect(female).Volume()
 orientation_checks.append(dict(entry_angle_deg=a,blocked=vol>.01,interference_mm3=vol))
 assert vol>.01,orientation_checks[-1]
report=dict(parameters=P,checks=checks,wrong_orientation_checks=orientation_checks,parts={n:dict(valid=s.isValid(),solids=len(s.Solids()),volume_mm3=s.Volume()) for n,s in parts.items()})
(ROOT/'parameters.json').write_text(json.dumps(P,indent=2));(ROOT/'validation.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
