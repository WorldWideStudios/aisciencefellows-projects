from pathlib import Path
import numpy as np
import cadquery as cq
import vtk
from vtk.util.numpy_support import numpy_to_vtk
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'diagrams';OUT.mkdir(exist_ok=True)
def rgb(h):return tuple(int(h[i:i+2],16)/255 for i in [1,3,5])
def render(name,items,cam=(75,58,-95),target=(0,0,10),scale=42,size=(1600,1100)):
 ren=vtk.vtkRenderer();ren.SetBackground(1,1,1)
 for s,color in items:
  verts,tri=s.tessellate(.06,.12)
  pts=vtk.vtkPoints();pts.SetData(numpy_to_vtk(np.array([v.toTuple() for v in verts]),deep=True))
  cells=vtk.vtkCellArray()
  for t in tri:
   cells.InsertNextCell(3)
   for v in t:cells.InsertCellPoint(v)
  poly=vtk.vtkPolyData();poly.SetPoints(pts);poly.SetPolys(cells)
  normals=vtk.vtkPolyDataNormals();normals.SetInputData(poly);normals.SetFeatureAngle(45);normals.Update()
  mapper=vtk.vtkPolyDataMapper();mapper.SetInputConnection(normals.GetOutputPort())
  actor=vtk.vtkActor();actor.SetMapper(mapper);actor.GetProperty().SetColor(*rgb(color));actor.GetProperty().SetAmbient(.3);actor.GetProperty().SetDiffuse(.7);actor.GetProperty().SetSpecular(.12);ren.AddActor(actor)
 win=vtk.vtkRenderWindow();win.SetOffScreenRendering(1);win.SetSize(*size);win.AddRenderer(ren);win.SetMultiSamples(4)
 camera=ren.GetActiveCamera();camera.SetPosition(*cam);camera.SetFocalPoint(*target);camera.SetViewUp(0,1,0);camera.ParallelProjectionOn();camera.SetParallelScale(scale)
 ren.ResetCameraClippingRange();win.Render()
 grab=vtk.vtkWindowToImageFilter();grab.SetInput(win);grab.Update()
 writer=vtk.vtkPNGWriter();writer.SetFileName(str(OUT/name));writer.SetInputConnection(grab.GetOutputPort());writer.Write();win.Finalize()

male=cq.importers.importStep(str(ROOT/'cad/male.step')).val()
female=cq.importers.importStep(str(ROOT/'cad/female.step')).val()
blue='#2678AE';orange='#DD9142'
render('male.png',[(male,blue)],cam=(40,32,65),target=(0,0,0),scale=25,size=(1200,1000))
render('female.png',[(female,orange)],cam=(35,50,-90),target=(0,0,10),scale=32,size=(1200,1000))
render('exploded.png',[(male.translate((0,0,-19)),blue),(female,orange)],cam=(70,60,-85),target=(0,0,4),scale=39,size=(1200,1000))
cut=female.intersect(cq.Workplane('XY').box(60,70,90).translate((-30,0,15)).val())
render('cutaway.png',[(male.rotate((0,0,0),(0,0,1),45),blue),(cut,orange)],cam=(90,35,35),target=(0,0,5),scale=30,size=(1200,1000))
fig,axs=plt.subplots(2,2,figsize=(15,12),facecolor='white')
fig.subplots_adjust(top=.87,bottom=.07,wspace=.04,hspace=.18)
fig.text(.06,.955,'Design 2 — three-dowel keyhole coupling',fontsize=25,weight='bold',color='#203046')
fig.text(.06,.915,'Single entry orientation • internal narrowing slot • 3 dowels • 45° turn • no pin lock',fontsize=14,color='#56667A')
for ax,name,title in zip(axs.flat,['male','female','exploded','cutaway'],['Male / asymmetric key head on narrow neck','Female / one-way entry + internal flared slot','Insert straight, then turn 45°','Seated / receiver cut away to expose capture']):
 ax.imshow(plt.imread(OUT/(name+'.png')));ax.axis('off');ax.set_title(title,loc='left',fontsize=13)
fig.text(.06,.025,'Dimensions in mm. Prototype geometry; physical fit, preload and reverse-torque retention require testing.',fontsize=11,color='#56667A')
fig.savefig(OUT/'design_overview.png',dpi=150)
