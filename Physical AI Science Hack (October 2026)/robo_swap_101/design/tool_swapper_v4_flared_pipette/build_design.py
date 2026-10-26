"""Combine the v2 flared-dowel coupling with the fitted v3 31 mm pipette collar.
All dimensions in mm. Female export stays in the original collar coordinates:
pipette bore along X, receiver opening along +Z. Male print export has its rear
mounting face at Z=0 and coupling projections pointing +Z.
"""
from pathlib import Path
import hashlib,json,math
import cadquery as cq
import manifold3d as md
import numpy as np
import trimesh as tm

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'cad'; OUT.mkdir(exist_ok=True)
SRC=ROOT/'inputs'; V=cq.Vector
CUT_Z=15.65
RECEIVER_HEIGHT=12.
RECEIVER_RADIUS=20.5
BLEND_HEIGHT=3.5
FACE_Z=CUT_Z+RECEIVER_HEIGHT
TURN=45.; DRAW=.8
H=7/math.sqrt(2)
PARAMS={
 'mount_bolt_circle_mm':14,'mount_hole_centers_xy_mm':[[x,y] for x in [-H,H] for y in [-H,H]],
 'mount_shank_clearance_diameter_mm':3.2,'screw_head_access_diameter_mm':6.2,
 'mount_base_diameter_mm':28,'mount_base_thickness_mm':4,
 'horn_recess_diameter_mm':20.4,'horn_recess_depth_mm':1,'screw_bearing_web_mm':3,
 'screw_nominal':'M3 x 6','screw_projection_beyond_horn_bearing_plane_mm':3,
 'spacer_height_mm':5,'spacer_outer_diameter_mm':27,'spacer_inner_diameter_mm':21,
 'dowel_plate_diameter_mm':40,'dowel_plate_thickness_mm':4,
 'male_rear_to_dowel_plate_face_mm':13,'male_total_height_mm':21,
 'male_print_z_levels_mm':{'rear':0,'horn_bearing':1,'screw_seat':4,'spacer_top_plate_underside':9,'dowel_face':13,'pin_tips':21},
 'dowel_count':3,'dowel_stem_diameter_mm':3.6,'dowel_head_diameter_mm':6,
 'dowel_projection_mm':8,'dowel_circle_diameter_mm':30,
 'turn_degrees':TURN,'nominal_axial_draw_in_mm':DRAW,
 'female_receiver_envelope_mm':[41,41,12],'female_receiver_shape':'circular upper body with rounded rectangular tapered base','receiver_base_mm':[34,28],'receiver_base_corner_radius_mm':5,'receiver_blend_height_mm':BLEND_HEIGHT,'minimum_nominal_outer_wall_mm':2.2,'minimum_nominal_socket_floor_mm':3.5,'original_collar_trim_plane_z_mm':CUT_Z,'female_entry_face_z_mm':FACE_Z,
 'pipette_bore_nominal_diameter_mm':31,'pipette_bore_cutter_diameter_mm':31.002,
 'pin_lock':False,
 'assembly_transform':'Male print mesh: translate Z -13, rotate local Z 0..45 deg, translate local Z -.8..0, rotate X 180 deg, translate global Z 27.65',
}
def cylinder(r,h,x=0,y=0,z=0):return cq.Solid.makeCylinder(r,h,V(x,y,z))
def cqbox(x,y,z,c):return cq.Workplane('XY').box(x,y,z).translate(c).val()
def mesh(shape):
 v,f=shape.tessellate(.025,.06)
 return tm.Trimesh(np.array([p.toTuple() for p in v]),np.array(f))
def manifold(m):
 s=md.Manifold(md.Mesh64(vert_properties=np.asarray(m.vertices,dtype=np.float64),tri_verts=np.asarray(m.faces,dtype=np.uint64)))
 assert s.status()==md.Error.NoError,s.status()
 return s

def tomesh(s):
 a=s.to_mesh64();return tm.Trimesh(np.asarray(a.vert_properties)[:,:3],np.asarray(a.tri_verts))
def boolean(operation,*meshes):
 result=md.Manifold.batch_boolean([manifold(m) for m in meshes],{'union':md.OpType.Add,'difference':md.OpType.Subtract,'intersection':md.OpType.Intersect}[operation])
 assert result.status()==md.Error.NoError
 return tomesh(result.simplify(0.00001))
def box(bounds):
 b=np.array(bounds);return tm.creation.box(extents=b[1]-b[0],transform=tm.transformations.translation_matrix(b.mean(0)))
def tcyl(r,z0,z1,x=0,y=0,sections=192):
 return tm.creation.cylinder(radius=r,height=z1-z0,sections=sections,transform=tm.transformations.translation_matrix([x,y,(z0+z1)/2]))
def placed(m,angle=0,offset=-DRAW):
 # Match the exported female face datum after STL float32 rounding (~1.5e-6 mm).
 m=m.copy();m.apply_translation([0,0,-13]);m.apply_transform(tm.transformations.rotation_matrix(math.radians(angle),[0,0,1]));m.apply_translation([0,0,offset]);m.apply_transform(tm.transformations.rotation_matrix(math.pi,[1,0,0]));m.apply_translation([0,0,float(np.float32(FACE_Z))]);return m

def intersect_volume(a,b):
 return float(abs((a^b).volume()))

# Reuse the coupling features exactly; rebuild only the wrist-side support.
v2male=cq.importers.importStep(str(SRC/'v2_male.step')).val()
features=v2male.intersect(cqbox(50,50,8.001,(0,0,4.0005)))
base=cylinder(14,4,z=-13).cut(cylinder(10.2,1.001,z=-13.001)).cut(cylinder(2.7,4.002,z=-13.001))
spacer=cylinder(13.5,5,z=-9).cut(cylinder(10.5,5.002,z=-9.001))
plate=cylinder(20,4,z=-4)
male=base.fuse(spacer).fuse(plate).fuse(features)
for x in [-H,H]:
 for y in [-H,H]:
  male=male.cut(cylinder(1.6,4.02,x,y,-13.01))
  male=male.cut(cylinder(3.1,18.02,x,y,-9))
male=male.clean().translate((0,0,13))
assert male.isValid() and len(male.Solids())==1
cq.exporters.export(male,str(OUT/'male_SO101_flared_5mm_spacer.step'))
cq.exporters.export(male,str(OUT/'male_SO101_flared_5mm_spacer.stl'),tolerance=.025,angularTolerance=.06)
print('Male built: original v2 key/dowels, 5 mm spacer, SO101 mount.',flush=True)

# Keep only the v2 receiver, replacing its unused rectangular rear blank with
# the original v3 collar. The old socket above Z15.65 is removed completely.
f0=tm.load(SRC/'pipette_collar_31mm_fitted.stl')
kept=boolean('intersection',f0,box([[-60,-60,-60],[60,60,CUT_Z]]))
v2female=cq.importers.importStep(str(SRC/'v2_female.step')).val()
# Trim the receiver to a circular boss, with a narrower rounded base that
# blends into the original collar. The full-diameter section contains every
# key/dowel cavity; only solid material below the cavities is tapered.
# Match eight ordered edges in both profiles so the blend does not twist
# between a single circle seam and the rounded rectangle's eight boundaries.
base_points=[(17,9),(12,14),(-12,14),(-17,9),(-17,-9),(-12,-14),(12,-14),(17,-9)]
d=5/math.sqrt(2)
corner_midpoints={0:(12+d,9+d),2:(-12-d,9+d),4:(-12-d,-9-d),6:(12+d,-9-d)}
angles=np.unwrap([math.atan2(y,x) for x,y in base_points])
base_edges=[];round_edges=[]
for i,(x,y) in enumerate(base_points):
 j=(i+1)%8;nx,ny=base_points[j]
 a=V(x,y,CUT_Z);b=V(nx,ny,CUT_Z)
 if i in corner_midpoints:
  mx,my=corner_midpoints[i];base_edges.append(cq.Edge.makeThreePointArc(a,V(mx,my,CUT_Z),b))
 else:base_edges.append(cq.Edge.makeLine(a,b))
 theta0=float(angles[i]);theta1=float(angles[j]) if j else float(angles[0]+2*math.pi)
 def circular_point(t):return V(RECEIVER_RADIUS*math.cos(t),RECEIVER_RADIUS*math.sin(t),CUT_Z+BLEND_HEIGHT)
 round_edges.append(cq.Edge.makeThreePointArc(circular_point(theta0),circular_point((theta0+theta1)/2),circular_point(theta1)))
base_wire=cq.Wire.assembleEdges(base_edges);round_wire=cq.Wire.assembleEdges(round_edges)
blend=cq.Solid.makeLoft([base_wire,round_wire],ruled=True)
upper=cylinder(RECEIVER_RADIUS,RECEIVER_HEIGHT-BLEND_HEIGHT,z=CUT_Z+BLEND_HEIGHT)
outer=blend.fuse(upper).clean()
original_socket=v2female.rotate((0,0,0),(1,0,0),180).translate((0,0,FACE_Z))
socket=original_socket.intersect(outer).clean()
assert socket.isValid() and len(socket.Solids())==1
socket_volume=socket.Volume()
cq.exporters.export(socket,str(OUT/'female_receiver_component.step'))
socket_mesh=mesh(socket)
female=boolean('union',kept,socket_mesh)
# Preserve a completely open shaft passage at the joint, with original bore size.
bore=tm.creation.cylinder(radius=15.501,height=100,sections=512,transform=tm.transformations.rotation_matrix(math.pi/2,[0,1,0]))
female=boolean('difference',female,bore)
female.export(OUT/'female_flared_pipette_collar_31mm.stl')
print('Female built: compact round socket, tapered base, preserved fitted v3 collar.',flush=True)

# STL's float32 coordinates can collapse tiny boolean seam triangles. Remove
# only zero-area or duplicate faces after this rounding, then reimport again.
cleanup={}
for name in ['male_SO101_flared_5mm_spacer.stl','female_flared_pipette_collar_31mm.stl']:
 p=OUT/name;m=tm.load(p);before=len(m.faces);vol=m.volume
 m.update_faces(m.nondegenerate_faces());m.update_faces(m.unique_faces());m.remove_unreferenced_vertices()
 cleanup[name]={'collapsed_or_duplicate_triangles_removed':before-len(m.faces),'volume_change_mm3':float(abs(m.volume-vol))}
 assert abs(m.volume-vol)<.001
 m.export(p)
# Validate the exported/reimported printable meshes, including the whole collar.
male_mesh=tm.load(OUT/'male_SO101_flared_5mm_spacer.stl');female_mesh=tm.load(OUT/'female_flared_pipette_collar_31mm.stl')
fsolid=manifold(female_mesh);msolid=manifold(male_mesh)
shaft=tm.creation.cylinder(radius=15.5,height=100,sections=512,transform=tm.transformations.rotation_matrix(math.pi/2,[0,1,0]));shaft_solid=manifold(shaft)
checks={}
parts={}
for n,m in [('male',male_mesh),('female',female_mesh)]:
 parts[n]={'watertight':bool(m.is_watertight),'winding_consistent':bool(m.is_winding_consistent),'solid_count':len(m.split()),'bounds_mm':m.bounds.tolist(),'volume_mm3':float(m.volume)}
 assert m.is_watertight and m.is_winding_consistent and len(m.split())==1,parts[n]
# M3x6 seat at z=4, pass a 3 mm web to the horn plane at z=1.
checks['M3_shank_max_interference_mm3']=max(intersect_volume(msolid,manifold(tcyl(1.5,-2,4,x,y))) for x in [-H,H] for y in [-H,H])
checks['6mm_head_and_tool_access_max_interference_mm3']=max(intersect_volume(msolid,manifold(tcyl(3,4.001,25,x,y))) for x in [-H,H] for y in [-H,H])
checks['20mm_horn_max_interference_mm3']=intersect_volume(msolid,manifold(tcyl(10,.001,.999)))
checks['central_horn_screw_relief_interference_mm3']=intersect_volume(msolid,manifold(tcyl(2.6,-1,3.999)))
checks['shaft_female_interference_mm3']=intersect_volume(fsolid,shaft_solid)
print('Checking full insertion and turn, screw access, and pipette passage...',flush=True)
checks['insertion_max_interference_mm3']=max(intersect_volume(manifold(placed(male_mesh,0,float(dz))),fsolid) for dz in np.linspace(-10,-.8,38))
checks['twist_max_interference_mm3']=max(intersect_volume(manifold(placed(male_mesh,float(a),-DRAW+DRAW*a/TURN)),fsolid) for a in np.linspace(0,45,91))
checks['shaft_male_during_twist_max_interference_mm3']=max(intersect_volume(manifold(placed(male_mesh,float(a),-DRAW+DRAW*a/TURN)),shaft_solid) for a in np.linspace(0,45,46))
checks['locked_withdrawal_1mm_interference_mm3']=intersect_volume(manifold(placed(male_mesh,45,-1)),fsolid)
checks['wrong_entry_180deg_interference_mm3']=intersect_volume(manifold(placed(male_mesh,180,-6)),fsolid)
# A continuous ring around every track confirms trimming has not opened
# the head pockets through the outside wall. A small margin accommodates
# faceted STL surfaces at the outer cylinder.
wall_gauge=boolean('difference',tcyl(20.45,CUT_Z+BLEND_HEIGHT+.01,FACE_Z-.01,sections=256),tcyl(18.5,CUT_Z+BLEND_HEIGHT,FACE_Z,sections=256))
checks['outer_wall_gauge_missing_material_mm3']=float(abs((manifold(wall_gauge)-fsolid).volume()))
# Verify the retained lower holder is identical to the supplied STL, both ways.
region=box([[-60,-60,-60],[60,60,CUT_Z-.0001]])
original_kept=manifold(boolean('intersection',f0,region))
new_kept=manifold(boolean('intersection',female_mesh,region))
checks['preserved_collar_material_removed_mm3']=float(abs((original_kept-new_kept).volume()))
checks['preserved_collar_material_added_mm3']=float(abs((new_kept-original_kept).volume()))
# Verify the positive v2 coupling features did not change when adding spacer.
feature_region=box([[-50,-50,13.0001],[50,50,22]])
old_feature_mesh=mesh(v2male.translate((0,0,13)))
old_features=manifold(boolean('intersection',old_feature_mesh,feature_region))
new_features=manifold(boolean('intersection',male_mesh,feature_region))
checks['v2_feature_symmetric_difference_mm3']=float(abs((old_features-new_features).volume())+abs((new_features-old_features).volume()))
for n,v in checks.items():
 if n in ['locked_withdrawal_1mm_interference_mm3','wrong_entry_180deg_interference_mm3']:assert v>1,(n,v)
 elif n=='v2_feature_symmetric_difference_mm3':assert v<.03,(n,v) # tessellation tolerance
 else:assert v<.001,(n,v)
# Independent remeasurement of reference hole centers from the cached official STEP.
reference_path=ROOT.parent/'tool_swapper_v1/reference/Wrist_Roll_Follower_SO101.step'
reference=cq.importers.importStep(str(reference_path)).val()
centers=[]
for face in reference.Faces():
 if face.geomType()=='CYLINDER':
  from OCP.BRepAdaptor import BRepAdaptor_Surface
  c=BRepAdaptor_Surface(face.wrapped).Cylinder()
  if abs(c.Radius()-1.6)<1e-5 and abs(abs(c.Axis().Direction().Z())-1)<1e-5:
   v=c.Location();xy=[v.X(),v.Y()]
   if not any(np.linalg.norm(np.array(xy)-q)<1e-5 for q in centers):centers.append(xy)
centered=np.asarray(centers)-np.mean(centers,axis=0)
expected=np.asarray(PARAMS['mount_hole_centers_xy_mm'])
assert len(centered)==4,centered
mount_error=max(min(np.linalg.norm(p-q) for q in expected) for p in centered)
assert mount_error<1e-5
previous=json.loads((ROOT/'reference/previous_square_validation.json').read_text())
old_female_volume=previous['parts']['female']['volume_mm3']
shape_change={'previous_receiver_envelope_mm':[44,44,18],'new_receiver_envelope_mm':[41,41,12],'height_reduction_mm':6,'new_receiver_volume_mm3':socket_volume,'previous_complete_female_volume_mm3':old_female_volume,'new_complete_female_volume_mm3':float(female_mesh.volume),'complete_female_volume_reduction_percent':100*(1-female_mesh.volume/old_female_volume)}
male_unchanged=hashlib.sha256((OUT/'male_SO101_flared_5mm_spacer.stl').read_bytes()).hexdigest()==json.loads((ROOT/'reference/male_before_trim_sha256.json').read_text())['sha256']
assert male_unchanged
report={'parameters':PARAMS,'shape_change':shape_change,'male_stl_identical_to_before_receiver_trim':male_unchanged,'checks':checks,'parts':parts,'stl_rounding_cleanup':cleanup,'reference_mount_max_center_error_mm':float(mount_error),'sampling':{'insertion_positions':38,'turn_positions':91,'shaft_turn_positions':46},'scope':'Nominal geometry checks, not measured hardware fit, structural proof, or preload validation.'}
(ROOT/'validation.json').write_text(json.dumps(report,indent=2))
(ROOT/'parameters.json').write_text(json.dumps(PARAMS,indent=2))
(ROOT/'provenance.json').write_text(json.dumps({str(p.relative_to(ROOT)):{'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in SRC.iterdir() if p.is_file()},indent=2))
placed(male_mesh,45,0).export(OUT/'male_assembled_DISPLAY_ONLY.stl')
print(json.dumps(report,indent=2),flush=True)
