"""Add a thin continuous backing wall to the fitted v3 male. Units: mm."""
from pathlib import Path
import json, math, hashlib, warnings
import numpy as np
import trimesh as tm
import manifold3d as md
warnings.filterwarnings('ignore',category=RuntimeWarning)
OUT=Path(__file__).resolve().parent
SRC=OUT.parent/'tool_swapper_v3'
def boolean(op,meshes):
 solids=[md.Manifold(md.Mesh64(vert_properties=np.asarray(m.vertices,dtype=np.float64),tri_verts=np.asarray(m.faces,dtype=np.uint64))) for m in meshes]
 for s in solids: assert s.status()==md.Error.NoError
 r=md.Manifold.batch_boolean(solids,{'union':md.OpType.Add,'difference':md.OpType.Subtract,'intersection':md.OpType.Intersect}[op]).simplify(.00001).to_mesh64()
 return tm.Trimesh(np.asarray(r.vert_properties)[:,:3],np.asarray(r.tri_verts))
def cyl(r,z0,z1,x=0,y=0):
 return tm.creation.cylinder(radius=r,height=z1-z0,sections=512,transform=tm.transformations.translation_matrix([x,y,(z0+z1)/2]))
def overlap(a,b):
 m=boolean('intersection',[a,b]);return abs(float(m.volume)) if len(m.faces) else 0.
def placed(m,angle=0,lift=0):
 m=m.copy();m.apply_transform(tm.transformations.rotation_matrix(np.pi,[1,0,0]));m.apply_transform(tm.transformations.rotation_matrix(math.radians(angle),[0,0,1]));m.apply_translation([0,0,29.65+lift]);return m
old=tm.load(SRC/'male_v3_SO101_fitted.stl')
female=tm.load(SRC/'pipette_collar_31mm_fitted.stl')
# Continuous annular wall around the dowel-root band. Existing head bores become D-shaped.
sleeve=boolean('difference',[cyl(10.1,4,11),cyl(9.8,3.9,11.1)])
male=boolean('union',[old,sleeve])
path=OUT/'male_v3_SO101_thin_wall.stl';male.export(path);male=tm.load(path)
p=7/math.sqrt(2)
shaft=tm.creation.cylinder(radius=15.5,height=80,sections=512,transform=tm.transformations.rotation_matrix(np.pi/2,[0,1,0]))
# A gauge annulus wholly within the nominal backing wall proves no open side gaps.
wall_gauge=boolean('difference',[cyl(10.09,6.49,9.51),cyl(9.81,6.48,9.52)])
missing_wall=boolean('difference',[wall_gauge,male])
# Check preserved radial dowel axes and exposed 3 mm circular sections.
dowel_checks=[]
for a in [0,120,240]:
 theta=math.radians(a);direction=np.array([math.cos(theta),math.sin(theta),0]);tangent=np.array([-math.sin(theta),math.cos(theta),0])
 sec=male.section(plane_origin=direction*12,plane_normal=direction)
 assert sec is not None
 pts=sec.vertices
 pts=pts[(pts[:,2]>6)&(pts[:,2]<10)]
 diameter_t=float(np.ptp(pts@tangent));diameter_z=float(np.ptp(pts[:,2]))
 assert abs(diameter_t-3)<.005 and abs(diameter_z-3)<.005
 dowel_checks.append({'angle_degrees':a,'tangential_diameter_mm':diameter_t,'vertical_diameter_mm':diameter_z})
# Coincident-face differences of STL meshes can produce spurious slivers.
# Check original surface vertices and triangle centers for actual loss instead.
old_samples=np.vstack([old.vertices,old.triangles_center])
_,distance,_=tm.proximity.closest_point(male,old_samples)
far_samples=old_samples[distance>1e-5]
outside_count=int(np.count_nonzero(~male.contains(far_samples))) if len(far_samples) else 0
checks={
 'watertight':bool(male.is_watertight),
 'winding_consistent':bool(male.is_winding_consistent),
 'solid_count':len(male.split()),
 'added_material_mm3':float(male.volume-old.volume),
 'original_surface_samples_outside_by_more_than_0p00001mm':outside_count,
 'backing_wall_gauge_missing_material_mm3':abs(float(missing_wall.volume)),
 'M3_shank_max_interference_mm3':max(overlap(male,cyl(1.5,1,4,x,y)) for x in [-p,p] for y in [-p,p]),
 '5p5mm_screw_head_access_max_interference_mm3':max(overlap(male,cyl(2.75,4.001,17,x,y)) for x in [-p,p] for y in [-p,p]),
 '6mm_screw_head_access_max_interference_mm3':max(overlap(male,cyl(3,4.001,17,x,y)) for x in [-p,p] for y in [-p,p]),
 'insertion_max_interference_mm3':max(overlap(placed(male,lift=float(h)),female) for h in np.linspace(0,18,73)),
 'turn_max_interference_mm3':max(overlap(placed(male,float(a)),female) for a in np.linspace(0,45,181)),
 'shaft_max_interference_mm3':max(overlap(placed(male,float(a)),shaft) for a in np.linspace(0,45,46)),
 'locked_1mm_withdrawal_interference_mm3':overlap(placed(male,45,1),female),
 'dowel_sections':dowel_checks,
 'parameters':{'outer_wall_diameter_mm':20.2,'inner_wall_diameter_mm':19.6,'wall_thickness_mm':.3,'wall_z_bounds_mm':[4,11],'dowel_z_bounds_mm':[6.5,9.5],'nominal_socket_radial_clearance_mm':.15,'maximum_checked_screw_head_diameter_mm':5.5,'screw_head_clearance_at_wall_mm':.05,'dowel_diameter_mm':3,'dowel_projection_from_new_wall_mm':2.9,'male_height_mm':14,'female_changed':False},
 'source_sha256':{name:hashlib.sha256((SRC/name).read_bytes()).hexdigest() for name in ['male_v3_SO101_fitted.stl','pipette_collar_31mm_fitted.stl']}
}
assert checks['watertight'] and checks['winding_consistent'] and checks['solid_count']==1
for k in ['original_surface_samples_outside_by_more_than_0p00001mm','backing_wall_gauge_missing_material_mm3','M3_shank_max_interference_mm3','5p5mm_screw_head_access_max_interference_mm3','insertion_max_interference_mm3','turn_max_interference_mm3','shaft_max_interference_mm3']: assert checks[k]<.001,(k,checks[k])
assert checks['locked_1mm_withdrawal_interference_mm3']>1
assert checks['6mm_screw_head_access_max_interference_mm3']>1
(OUT/'validation.json').write_text(json.dumps(checks,indent=2));print(json.dumps(checks,indent=2))
