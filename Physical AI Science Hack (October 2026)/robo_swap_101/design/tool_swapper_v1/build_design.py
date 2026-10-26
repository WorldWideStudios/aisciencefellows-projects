"""SO-101 quarter-turn tool swapper, millimetres. Prototype, not load-rated.
Coordinates: z = insertion, y = up. Male seated datum at z=0.
Build: .cad-venv/bin/python build_design.py (from this directory).
"""
from pathlib import Path
import math, json
import cadquery as cq
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'cad'; OUT.mkdir(exist_ok=True)
V=cq.Vector
LEAD=8.0
BOLT_R=7.0
HOLE=BOLT_R/math.sqrt(2)
PARAMS=dict(male_major_diameter=10,male_core_diameter=8,insertion=10,
 initial_insertion=8,twist_degrees=90,draw_in=2,equivalent_lead=LEAD,
 lug_centres=[3,7],lug_arc_degrees=36,lug_axial_height=1.2,
 female_core_diameter=8.4,groove_outer_diameter=10.6,groove_height=1.8,
 mouth_diameter=12,mouth_depth=1.8,bore_depth=11.2,
 mount_bolt_circle=14,mount_holes=3.2,mount_counterbores=6.2,
 mount_square=2*HOLE,mount_web=3,mount_diameter=28,mount_thickness=7,
 entry_slot_angle=60,face_gasket_id=21,face_gasket_od=24,face_gasket_groove_depth=.3,
 female_body=[32,28,22],tool_blank=[24,24,18],latch_pin_diameter=2,
 latch_hole_diameter=2.3,latch_travel=3,latch_engagement=1.5)

def cylinder(r,h,p=(0,0,0),d=(0,0,1)):
 return cq.Solid.makeCylinder(r,h,V(*p),V(*d))
def box(x,y,z,p):
 return cq.Workplane('XY').box(x,y,z).translate(p).val()
def helical_sector(a0,a1,zc,r0,r1,height,phase=0):
 # Rectangular radial sections; z increases with angle. Positive angle
 # is the tightening direction. Both opposing starts use the same phase.
 wires=[]
 n=max(3,int((a1-a0)/6)+1)
 for i in range(n+1):
  a=a0+(a1-a0)*i/n;t=math.radians(a+phase);z=zc+LEAD*a/360
  pts=[V(r*math.cos(t),r*math.sin(t),zz) for r,zz in
       [(r0,z-height/2),(r1,z-height/2),(r1,z+height/2),(r0,z+height/2)]]
  wires.append(cq.Wire.makePolygon(pts,close=True))
 return cq.Solid.makeLoft(wires,ruled=False)

# Male: the four M3 screw heads are reachable from the tool-facing side.
male=cylinder(14,7,(0,0,-7))
male=male.cut(cylinder(10,1.001,(0,0,-7.001))) # original 20 mm horn recess
male=male.cut(cylinder(2.7,4.001,(0,0,-7.001))) # central horn screw clearance
male=male.cut(cylinder(12,.301,(0,0,-.3)).cut(cylinder(10.5,.301,(0,0,-.3))))
for x in [-HOLE,HOLE]:
 for y in [-HOLE,HOLE]:
  male=male.cut(cylinder(1.6,7.02,(x,y,-7.01)))
  male=male.cut(cylinder(3.1,3.01,(x,y,-3)))
male=male.fuse(cylinder(4,8.5))
male=male.fuse(cq.Solid.makeCone(4,3,1.5,V(0,0,8.5),V(0,0,1)))
for zc in [3,7]:
 for phase in [0,180]:
  male=male.fuse(helical_sector(-18,18,zc,3.8,5,1.2,phase))
# Cross-hole starts along x; after 90 degrees it aligns with vertical lock pin.
male=male.cut(cylinder(1.15,12,(-6,0,5),(1,0,0))).clean()

female=box(32,28,22,(0,0,11)).fuse(box(24,24,18,(0,0,31)))
female=female.cut(cylinder(4.2,11.2))
female=female.cut(cq.Solid.makeCone(6,4.2,1.8,V(0,0,0),V(0,0,1)))
# Two wide entry slots. The sectors accommodate all four screw segments.
for phase in [0,180]:
 # Straight slots formed by extruding a sector face (angular clearance 12 deg).
 pts=[(0,0)]+[(5.3*math.cos(math.radians(a+phase)),5.3*math.sin(math.radians(a+phase))) for a in range(-30,31,2)]+[(0,0)]
 slot=cq.Workplane('XY').polyline(pts).close().extrude(10.5).val()
 female=female.cut(slot)
 for zc in [3,7]:
  female=female.cut(helical_sector(-30,108,zc-2,3.9,5.3,1.8,phase))
# Lock pin and two guide screws (M3 pilot holes; spring guides are hardware).
female=female.cut(cylinder(1.15,13,(0,2,5),(0,1,0)))
for x in [-10,10]:
 female=female.cut(cylinder(1.25,6.01,(x,8,5),(0,1,0)))
# Flush steel targets for light magnetic parking retention. The magnets live
# in the rack; they only hold against the latch springs while parked.
for x in [-10,10]:
 female=female.cut(cylinder(3.1,.85,(x,-14,16),(0,1,0)))
 female=female.cut(cylinder(.8,5,(x,-14,16),(0,1,0)))
female=female.clean()

# Sliding yoke carries a 2 mm steel pin. Springs on two fixed M3 guide screws
# push it down. The rack floor lifts its feet by 3 mm to release the pin.
yoke=box(40,3,6,(0,16.5,5))
for x in [-18.5,18.5]:
 yoke=yoke.fuse(box(3,33.5,6,(x,-.25,5)))
for x in [-10,10]:
 yoke=yoke.cut(cylinder(1.7,3.2,(x,14.9,5),(0,1,0)))
yoke=yoke.cut(cylinder(1.0,3.2,(0,14.9,5),(0,1,0))).clean()
pin=cylinder(1,15.5,(0,2.5,5),(0,1,0))
# Guide rods / heads are represented as envelopes, not manufactured threads.
guides=[];springs=[]
for x in [-10,10]:
 guides.append(cylinder(1.5,20,(x,8,5),(0,1,0)).fuse(cylinder(3,1.5,(x,28,5),(0,1,0))))
 # Spring wire envelope with 6 mm OD and 3.5 mm ID. Hardware selection pending.
 springs.append(cylinder(3,10,(x,18,5),(0,1,0)).cut(cylinder(1.75,10,(x,18,5),(0,1,0))))

# Open-top cradle concept: front and rear lips resist screw-in and screw-out
# forces. Guides at rear leave the yoke free at z=2..8.
rack=box(50,4,28,(0,-16,11))
for x in [-23.5,23.5]:
 rack=rack.fuse(box(3,14,28,(x,-7,11)))
for x in [-18.65,18.65]:
 rack=rack.fuse(box(4.7,14,8,(x,-7,16)))
for x in [-19.9,19.9]:
 for z in [-3.2,23.7]:
  rack=rack.fuse(box(10.2,14,1.6 if z<0 else 2.6,(x,-7,z)))
for x in [-20,20]:
 rack=rack.cut(cylinder(2.2,4.2,(x,-18.1,11),(0,1,0)))
for x in [-10,10]:
 rack=rack.cut(cylinder(3.1,2.1,(x,-16.1,16),(0,1,0)))
rack=rack.clean()

parts={'male':male,'female':female,'latch_yoke':yoke,'latch_pin_envelope':pin,'rack_concept':rack}
for name,s in parts.items():
 assert s.isValid(), name+' invalid'
 assert len(s.Solids())==1,(name,len(s.Solids()))
 cq.exporters.export(s,str(OUT/(name+'.step')))
 cq.exporters.export(s,str(OUT/(name+'.stl')),tolerance=.04,angularTolerance=.08)

seated=male.rotate((0,0,0),(0,0,1),90)
assy=cq.Assembly(name='SO101_tool_swapper_v1')
for name,s,c in [('male',seated,(.12,.44,.72)),('female',female,(.87,.51,.15)),('release_yoke',yoke,(.16,.60,.40)),('steel_lock_pin',pin,(.5,.54,.6))]:
 assy.add(s,name=name,color=cq.Color(*c))
for i,s in enumerate(guides):assy.add(s,name=f'guide_screw_{i}',color=cq.Color(.55,.58,.63))
for i,s in enumerate(springs):assy.add(s,name=f'spring_envelope_{i}',color=cq.Color(.65,.68,.73))
assy.export(str(OUT/'assembled.step'))

# Mechanical clearance checks on core parts along the entire nominal motion.
checks=[]
for angle in range(0,91,15):
 m=male.rotate((0,0,0),(0,0,1),angle).translate((0,0,-2+angle/45))
 vol=m.intersect(female).Volume()
 checks.append(dict(angle_deg=angle,insertion_mm=8+angle/45,interference_mm3=vol))
 assert vol < .01,checks[-1]
# Insertion at zero angle, plus pin positions and rack geometry.
for offset in [-10,-8,-6,-4,-2]:
 vol=male.translate((0,0,offset)).intersect(female).Volume()
 checks.append(dict(straight_offset_mm=offset,interference_mm3=vol))
 assert vol<.01,checks[-1]
for label,a,b in [('pin/male seated',pin,seated),('pin/female',pin,female),('yoke/female',yoke,female),('rack/female',rack,female),('rack/released_yoke',rack,yoke.translate((0,3,0)))]:
 vol=a.intersect(b).Volume();checks.append(dict(pair=label,interference_mm3=vol));assert vol<.01,checks[-1]
for dz in [-2,-1,0]:
 for label,s in [('female',female),('released_yoke',yoke.translate((0,3,0)))]:
  vol=rack.intersect(s.translate((0,0,dz))).Volume()
  checks.append(dict(pair='rack/'+label,float_z_mm=dz,interference_mm3=vol));assert vol<.01,checks[-1]
report={'parameters_mm':PARAMS,'checks':checks,'parts':{n:{'valid':s.isValid(),'solids':len(s.Solids()),'volume_mm3':s.Volume()} for n,s in parts.items()}}
(ROOT/'validation.json').write_text(json.dumps(report,indent=2))
(ROOT/'parameters.json').write_text(json.dumps(PARAMS,indent=2))
print(json.dumps(report,indent=2))
