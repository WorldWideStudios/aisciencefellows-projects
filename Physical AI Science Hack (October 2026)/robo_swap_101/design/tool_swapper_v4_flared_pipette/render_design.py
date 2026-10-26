from pathlib import Path
import numpy as np
import trimesh as tm
import vtk
from vtk.util.numpy_support import numpy_to_vtk
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'diagrams';OUT.mkdir(exist_ok=True)
BLUE='#2678AE';ORANGE='#DD9142';INK='#203046';MUTED='#56667A'
def rgb(h):return tuple(int(h[i:i+2],16)/255 for i in [1,3,5])
def render(name,items,cam,target,scale,size=(1400,1100)):
 ren=vtk.vtkRenderer();ren.SetBackground(1,1,1)
 for mesh,col in items:
  points=vtk.vtkPoints();points.SetData(numpy_to_vtk(np.asarray(mesh.vertices),deep=True))
  cells=vtk.vtkCellArray()
  for tri in mesh.faces:
   cells.InsertNextCell(3)
   for i in tri:cells.InsertCellPoint(int(i))
  poly=vtk.vtkPolyData();poly.SetPoints(points);poly.SetPolys(cells)
  normals=vtk.vtkPolyDataNormals();normals.SetInputData(poly);normals.SetFeatureAngle(35);normals.Update()
  mapper=vtk.vtkPolyDataMapper();mapper.SetInputConnection(normals.GetOutputPort())
  actor=vtk.vtkActor();actor.SetMapper(mapper);actor.GetProperty().SetColor(*rgb(col));actor.GetProperty().SetAmbient(.28);actor.GetProperty().SetDiffuse(.72);actor.GetProperty().SetSpecular(.1);ren.AddActor(actor)
 win=vtk.vtkRenderWindow();win.SetOffScreenRendering(1);win.SetSize(*size);win.AddRenderer(ren);win.SetMultiSamples(4)
 camera=ren.GetActiveCamera();camera.SetPosition(*cam);camera.SetFocalPoint(*target);camera.SetViewUp(0,0,1);camera.ParallelProjectionOn();camera.SetParallelScale(scale)
 ren.ResetCameraClippingRange();win.Render()
 grab=vtk.vtkWindowToImageFilter();grab.SetInput(win);grab.Update()
 writer=vtk.vtkPNGWriter();writer.SetFileName(str(OUT/name));writer.SetInputConnection(grab.GetOutputPort());writer.Write();win.Finalize()
male=tm.load(ROOT/'cad/male_SO101_flared_5mm_spacer.stl')
female=tm.load(ROOT/'cad/female_flared_pipette_collar_31mm.stl')
render('male.png',[(male,BLUE)],(65,-85,90),(0,0,9),25)
render('female.png',[(female,ORANGE)],(100,-65,65),(0,0,2),33)
render('female_bore.png',[(female,ORANGE)],(110,0,9),(0,0,3),34)
assembled=tm.load(ROOT/'cad/male_assembled_DISPLAY_ONLY.stl')
exploded=assembled.copy();exploded.apply_translation([0,0,14])
render('exploded.png',[(exploded,BLUE),(female,ORANGE)],(110,-60,55),(0,0,13),48)
render('assembled.png',[(assembled,BLUE),(female,ORANGE)],(100,-60,50),(0,0,7),39)
# A real mesh section through one pair of mounting holes shows screw paths,
# web thickness, and the separate five-millimetre spacer height.
fig,ax=plt.subplots(figsize=(11,6),facecolor='white');ax.set_aspect('equal');ax.set_xlim(-23,28);ax.set_ylim(-5,25)
p=7/np.sqrt(2);sec=male.section(plane_origin=[0,p,0],plane_normal=[0,1,0])
for line in sec.discrete:ax.plot(line[:,0],line[:,2],color=BLUE,lw=1.5)
for x in [-p,p]:
 ax.add_patch(Rectangle((x-1.5,-2),3,6,facecolor='#778694',edgecolor='none',alpha=.6))
 ax.add_patch(Rectangle((x-2.75,4),5.5,3,facecolor='#778694',edgecolor='none',alpha=.6))
def dim(x,z0,z1,label):
 ax.annotate('',(x,z1),(x,z0),arrowprops=dict(arrowstyle='<->',lw=1,color=INK))
 ax.text(x+.5,(z0+z1)/2,label,va='center',color=INK,fontsize=10)
dim(21,4,9,'5 mm spacer');dim(16,1,4,'3 mm web');dim(21,9,13,'4 mm plate')
ax.axhline(1,color=MUTED,lw=.7,ls='--',xmin=.12,xmax=.72)
ax.text(-22,-3.8,'Horn bearing plane: Z = 1 mm',color=MUTED,fontsize=10)
ax.text(-22,22.8,'Section through mounting holes',color=INK,fontsize=15,weight='bold')
ax.text(-22,20.3,'M3 × 6 screws shown as gauges • Ø6.2 access bores',color=MUTED,fontsize=11)
ax.set_axis_off();fig.tight_layout();fig.savefig(OUT/'mount_section.png',dpi=170);plt.close(fig)
fig,axs=plt.subplots(2,2,figsize=(16,13),facecolor='white');fig.subplots_adjust(top=.89,bottom=.07,wspace=.06,hspace=.13)
fig.text(.06,.96,'Flared-dowel coupling + fitted 31 mm pipette collar',fontsize=23,weight='bold',color=INK)
fig.text(.06,.925,'Rounded Ø41 receiver • 12 mm socket height • 5 mm male spacer • original collar bore and clamp',fontsize=13,color=MUTED)
for ax,n,title in zip(axs.flat,['male','female','mount_section','assembled'],['Male: existing v2 coupling on a spaced mounting flange','Female: compact round socket with tapered base','Mounting: original screw engagement preserved','Assembly: pipette passage remains clear']):
 ax.imshow(plt.imread(OUT/(n+'.png')));ax.axis('off');ax.set_title(title,loc='left',fontsize=12,color=INK,pad=5)
fig.text(.06,.027,'Dimensions in mm. Prototype geometry verified digitally; actual screw fit, print tolerances and load capacity require a physical trial.',fontsize=10,color=MUTED)
fig.savefig(OUT/'design_overview.png',dpi=150);plt.close(fig)

# Matching camera and scale make the removed bulk easy to compare.
previous=tm.load(ROOT/'reference/previous_square_female_DISPLAY_ONLY.stl')
render('previous_square.png',[(previous,'#99A4AE')],(100,-65,65),(0,0,3),38)
render('compact_comparison_view.png',[(female,ORANGE)],(100,-65,65),(0,0,3),38)
fig,axs=plt.subplots(1,2,figsize=(14,8),facecolor='white');fig.subplots_adjust(top=.83,bottom=.10,wspace=.04)
fig.text(.055,.94,'A smaller receiver, shaped to meet the collar',fontsize=23,weight='bold',color=INK)
fig.text(.055,.889,'Same three-dowel interface and 31 mm holder • compatible with the existing male',fontsize=12,color=MUTED)
for ax,n,title in zip(axs,['previous_square','compact_comparison_view'],['Before — 44 × 44 × 18 mm block','After — Ø41 × 12 mm rounded receiver']):
 ax.imshow(plt.imread(OUT/(n+'.png')));ax.axis('off');ax.set_title(title,loc='left',fontsize=13,color=INK,pad=8)
import json
report=json.loads((ROOT/'validation.json').read_text());reduction=report['shape_change']['complete_female_volume_reduction_percent']
fig.text(.055,.04,f'6 mm shorter receiver • {reduction:.0f}% less material in the complete female part • tapered base joins the original collar',fontsize=12,color=MUTED)
fig.savefig(OUT/'receiver_comparison.png',dpi=160);plt.close(fig)
