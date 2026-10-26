"""Revise supplied v3 meshes. All dimensions mm. Requires trimesh, manifold3d, numpy."""
from pathlib import Path
import json, math, warnings
import numpy as np
import trimesh as tm
import manifold3d as md
warnings.filterwarnings('ignore',category=RuntimeWarning)
OUT=Path(__file__).resolve().parent
SRC=OUT/'inputs'
def boolean(op, meshes):
 solids=[md.Manifold(md.Mesh64(vert_properties=np.asarray(m.vertices,dtype=np.float64),tri_verts=np.asarray(m.faces,dtype=np.uint64))) for m in meshes]
 for solid in solids: assert solid.status()==md.Error.NoError,solid.status()
 operation={'union':md.OpType.Add,'difference':md.OpType.Subtract,'intersection':md.OpType.Intersect}[op]
 result=md.Manifold.batch_boolean(solids,operation).simplify(0.00001).to_mesh64()
 return tm.Trimesh(np.asarray(result.vert_properties)[:,:3],np.asarray(result.tri_verts))
def box(bounds):
 b=np.array(bounds);return tm.creation.box(extents=b[1]-b[0],transform=tm.transformations.translation_matrix(b.mean(0)))
def cyl(r,z0,z1,x=0,y=0):
 return tm.creation.cylinder(radius=r,height=z1-z0,sections=256,transform=tm.transformations.translation_matrix([x,y,(z0+z1)/2]))
def placed(m,angle=0,lift=0):
 m=m.copy();m.apply_transform(tm.transformations.rotation_matrix(np.pi,[1,0,0]));m.apply_transform(tm.transformations.rotation_matrix(np.radians(angle),[0,0,1]));m.apply_translation([0,0,29.65+lift]);return m
raw=tm.load(SRC/'male_v3.stl'); parts=raw.split(only_watertight=False)
original=max(parts,key=lambda p:abs(p.volume));original.fix_normals()
f0=tm.load(SRC/'pipette_collar_31mm.stl')
# Remove eight mm of plain cylindrical stem; preserve original tip and three tabs.
top=boolean('intersection',[original,box([[-30,-30,12],[30,30,30]])]);top.apply_translation([0,0,-8])
blank=boolean('union',[cyl(18,0,4),top])
# Standard SO101 four-hole horn: 14 mm bolt circle, square oriented 45 degrees.
p=7/math.sqrt(2); cuts=[]
for x in [-p,p]:
 for y in [-p,p]:
  cuts += [cyl(1.6,-1,16,x,y),cyl(3.1,4,16,x,y)]
cuts += [cyl(10.2,-1,1),cyl(2.7,-1,4)]
male=boolean('difference',[blank,*cuts])
# Clear the existing 31 mm clamp bore along X, including its marked obstruction.
bore=tm.creation.cylinder(radius=15.501,height=80,sections=512,transform=tm.transformations.rotation_matrix(np.pi/2,[0,1,0]))
gauge=bore.copy();gauge.vertices[:,1:]*=15.5/15.501
cleared=boolean('difference',[f0,bore])
# New 45-degree tracks for the shortened tabs. Keep a 1.8 mm top retaining lip.
# Core radius 10.25; track outer radius 13.4; sectors span -10..55 degrees
# around each of the three entry positions. Track Z limits: 19.45..23.85.
def sector(a0,a1,z0,z1,r=13.4):
 angles=np.radians(np.linspace(a0,a1,int(round(a1-a0))*2+1))
 polygon=np.vstack([[0,0],np.column_stack([r*np.cos(angles),r*np.sin(angles)])])
 n=len(polygon);verts=np.vstack([np.column_stack([polygon,np.full(n,z0)]),np.column_stack([polygon,np.full(n,z1)])]);faces=[]
 for i in range(1,n-1): faces += [[0,i+1,i],[n,n+i,n+i+1]]
 for i in range(n):
  j=(i+1)%n;faces += [[i,j,n+j],[i,n+j,n+i]]
 return tm.Trimesh(verts,faces)
tracks=[sector(a-10,a+55,19.45,23.85) for a in [0,120,240]]
sweep=boolean('union',[cyl(10.25,15.60,26),*tracks])
female=boolean('difference',[f0,bore,sweep])
male.export(OUT/'male_v3_SO101_fitted.stl');female.export(OUT/'pipette_collar_31mm_fitted.stl')
male=tm.load(OUT/'male_v3_SO101_fitted.stl');female=tm.load(OUT/'pipette_collar_31mm_fitted.stl')
def volume_intersection(a,b):
 v=boolean('intersection',[a,b]);return float(abs(v.volume)) if len(v.faces) else 0.
checks={}
checks['M3_shank_gauge_max_interference_mm3']=max(volume_intersection(male,cyl(1.5,1,4,x,y)) for x in [-p,p] for y in [-p,p])
checks['6mm_head_access_max_interference_mm3']=max(volume_intersection(male,cyl(3,4.01,16,x,y)) for x in [-p,p] for y in [-p,p])
checks['20mm_horn_gauge_interference_mm3']=volume_intersection(male,cyl(10,0.01,.99))
checks['insertion_max_interference_mm3']=max(volume_intersection(placed(male,lift=float(h)),female) for h in np.linspace(0,18,73))
checks['twist_max_interference_mm3']=max(volume_intersection(placed(male,float(a)),female) for a in np.linspace(0,45,181))
checks['shaft_bore_interference_female_mm3']=volume_intersection(female,gauge)
checks['shaft_bore_interference_male_max_mm3']=max(volume_intersection(placed(male,float(a)),gauge) for a in np.linspace(0,45,46))
checks['locked_axial_withdrawal_1mm_interference_mm3']=volume_intersection(placed(male,45,1),female)
checks['wrong_entry_45deg_interference_mm3']=max(volume_intersection(placed(male,45,float(h)),female) for h in np.linspace(0,8,33))
for label,m in [('male',male),('female',female)]:
 checks[label]={'watertight':bool(m.is_watertight),'winding_consistent':bool(m.is_winding_consistent),'solid_count':len(m.split()),'bounds_mm':m.bounds.tolist(),'volume_mm3':float(m.volume)}
 assert m.is_watertight and m.is_winding_consistent and len(m.split())==1
for k in ['M3_shank_gauge_max_interference_mm3','6mm_head_access_max_interference_mm3','20mm_horn_gauge_interference_mm3','insertion_max_interference_mm3','twist_max_interference_mm3','shaft_bore_interference_female_mm3','shaft_bore_interference_male_max_mm3']: assert checks[k]<.001,(k,checks[k])
assert checks['locked_axial_withdrawal_1mm_interference_mm3']>1
checks['parameters']={'hole_centers_xy_mm':[[x,y] for x in [-p,p] for y in [-p,p]],'bolt_circle_mm':14,'through_hole_diameter_mm':3.2,'head_access_diameter_mm':6.2,'horn_recess_diameter_mm':20.4,'horn_recess_depth_mm':1,'bearing_web_mm':3,'male_stem_removed_mm':8,'male_height_mm':14,'shaft_bore_mm':31,'turn_degrees':45,'track_z_bounds_mm':[19.45,23.85],'retaining_lip_mm':1.8,'track_outer_radius_mm':13.4,'bore_cutter_diameter_mm':31.002,'core_radial_clearance_mm':.25,'assembly_transform':'male rotate X 180 degrees, rotate Z 0..45 degrees, translate [0,0,29.65]'}
(OUT/'validation.json').write_text(json.dumps(checks,indent=2));print(json.dumps(checks,indent=2))
# Assembly meshes are for inspection only, not printing.
placed(male,45).export(OUT/'male_locked_display_only.stl')
