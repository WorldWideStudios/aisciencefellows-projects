from pathlib import Path
import json, math
import numpy as np
import cadquery as cq
import vtk
from vtk.util.numpy_support import numpy_to_vtk
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle,Rectangle,Polygon,Arc
ROOT=Path(__file__).resolve().parent; OUT=ROOT/'diagrams'; OUT.mkdir(exist_ok=True)
C={'male':'#2678AE','female':'#DD9142','latch_yoke':'#329B78','latch_pin_envelope':'#67778C','rack_concept':'#AAB3BE'}
parts={n:cq.importers.importStep(str(ROOT/'cad'/f'{n}.step')).val() for n in C}
parts['female_cutaway']=parts['female'].intersect(cq.Workplane('XY').box(40,80,100).translate((-20,0,20)).val())
cq.exporters.export(parts['female_cutaway'],str(ROOT/'cad'/'female_cutaway_display_only.stl'),tolerance=.06,angularTolerance=.12)

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

male=parts['male'];female=parts['female'];yoke=parts['latch_yoke'];pin=parts['latch_pin_envelope'];rack=parts['rack_concept']
render('male_render.png',[(male,C['male'])],cam=(35,28,45),target=(0,0,1),scale=18,size=(1100,950))
render('female_render.png',[(female,C['female']),(yoke,C['latch_yoke']),(pin,C['latch_pin_envelope'])],cam=(65,50,-80),target=(0,3,18),scale=30,size=(1100,950))
render('exploded_render.png',[(male.translate((0,0,-22)),C['male']),(female,C['female']),(yoke,C['latch_yoke']),(pin,C['latch_pin_envelope'])],cam=(100,52,-35),target=(0,1,4),scale=36)
seated=male.rotate((0,0,0),(0,0,1),90)
render('cutaway_render.png',[(seated,C['male']),(parts['female_cutaway'],C['female']),(pin,C['latch_pin_envelope'])],cam=(100,25,16),target=(0,0,10),scale=24)
render('docked_render.png',[(seated.translate((0,0,-2)),C['male']),(female.translate((0,0,-2)),C['female']),(yoke.translate((0,3,-2)),C['latch_yoke']),(pin.translate((0,3,-2)),C['latch_pin_envelope']),(rack,C['rack_concept'])],cam=(90,60,-90),target=(0,1,8),scale=37)
render('lifted_render.png',[(seated.translate((0,25,0)),C['male']),(female.translate((0,25,0)),C['female']),(yoke.translate((0,25,0)),C['latch_yoke']),(pin.translate((0,25,0)),C['latch_pin_envelope']),(rack,C['rack_concept'])],cam=(90,60,-90),target=(0,12,8),scale=46)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False})
INK='#203046';MUTED='#56667A'
def page(title,subtitle,rows=2,cols=2):
 fig,axs=plt.subplots(rows,cols,figsize=(15,11),facecolor='white')
 fig.subplots_adjust(top=.86,bottom=.12,left=.05,right=.95,wspace=.1,hspace=.32)
 fig.text(.05,.955,title,fontsize=24,weight='bold',color=INK)
 fig.text(.05,.915,subtitle,fontsize=12,color=MUTED)
 fig.text(.05,.025,'SO-101 tool swapper • v1 • Dimensions in mm • Prototype: physical fit and load testing required',fontsize=10,color=MUTED)
 return fig,axs
def pic(ax,file,title,caption):
 ax.imshow(plt.imread(OUT/file));ax.axis('off');ax.set_title(title,loc='left',fontsize=15,color=INK,pad=8)
 ax.text(0,-.02,caption,transform=ax.transAxes,va='top',color=MUTED,fontsize=10)
def save(fig,name):
 fig.savefig(OUT/(name+'.png'),dpi=160);fig.savefig(OUT/(name+'.svg'));plt.close(fig)
fig,axs=page('Quarter-turn tool swapper','Ø10 interrupted screw • 10 mm seated insertion • 8 mm slide + 2 mm draw-in over 90°')
pic(axs[0,0],'exploded_render.png','01  Side approach','Blue: robot-side male. Orange: receiver + unfinished tool blank.\nAlign the two pairs of interrupted screw segments with the entry slots.')
pic(axs[0,1],'cutaway_render.png','02  Seated / receiver cut away','Four short helical ribs engage the receiver. The flange seats on its face.\nThe grey pin blocks relative rotation; the mouth is chamfered for capture.')
pic(axs[1,0],'docked_render.png','03  In the rack / pin released','The floor raises the green yoke 3 mm. The rack prevents rotation.\n2 mm of axial float lets the screw draw the receiver toward the robot.')
pic(axs[1,1],'lifted_render.png','04  Lift out / pin engaged','Lift at least 20 mm to clear the cradle. Springs lower the yoke and pin.\nSpring / guide-screw hardware omitted in these views for clarity.')
save(fig,'01_assembly_and_sequence')
fig,axs=page('Part geometry and mounting','Original SO-101 follower gripper interface measured from upstream STEP; all new dimensions are proposed.')
pic(axs[0,0],'male_render.png','Male / gripper replacement','Ø28 × 7 flange. Existing wrist horn retained.\n4 × M3×6 fasteners through a 3 mm bearing web. Face gasket groove shown.')
pic(axs[0,1],'female_render.png','Female / receiver + tool blank','Receiver: 32 wide × 28 high × 22 deep.\nRear tool blank: 24 × 24 × 18. No pipette clamp or actuation designed.')
ax=axs[1,0];ax.set_aspect('equal');ax.set_xlim(-20,22);ax.set_ylim(-19,20);ax.axis('off');ax.set_title('Mount face / looking along wrist axis',loc='left',fontsize=15,color=INK)
a=7/math.sqrt(2)
ax.add_patch(Circle((0,0),14,fc='#E8F2F9',ec=C['male'],lw=1.5));ax.add_patch(Circle((0,0),7,fill=False,ec=MUTED,ls='--',lw=.8))
for x in [-a,a]:
 for y in [-a,a]:
  ax.add_patch(Circle((x,y),3.1,fc='white',ec=C['male'],lw=.8));ax.add_patch(Circle((x,y),1.6,fc='white',ec=INK,lw=1))
ax.add_patch(Circle((0,0),4,fc=C['male'],ec=INK,lw=.8))
ax.plot([-16,16],[0,0],c=MUTED,lw=.6,ls='-.');ax.plot([0,0],[-16,16],c=MUTED,lw=.6,ls='-.')
def dim(ax,p1,p2,text,offset=(0,0)):
 ax.annotate('',xy=p2,xytext=p1,arrowprops={'arrowstyle':'<->','lw':.8,'color':INK})
 ax.text((p1[0]+p2[0])/2+offset[0],(p1[1]+p2[1])/2+offset[1],text,ha='center',va='center',fontsize=10,color=INK,bbox={'facecolor':'white','edgecolor':'none','pad':1})
dim(ax,(-a,16),(a,16),'9.899',offset=(0,1.5));ax.plot([-a,-a],[a,17],c=MUTED,lw=.6);ax.plot([a,a],[a,17],c=MUTED,lw=.6)
ax.annotate('4 × Ø3.2\nØ6.2 head recess',xy=(a,-a),xytext=(8,-13),fontsize=10,color=INK,arrowprops={'arrowstyle':'-','lw':.8})
ax.annotate('Ø14 bolt circle',xy=(-7,0),xytext=(-20,-13),fontsize=10,color=INK,arrowprops={'arrowstyle':'-','lw':.8})
ax=axs[1,1];ax.set_aspect('equal');ax.axis('off');ax.set_xlim(-13,45);ax.set_ylim(-25,22);ax.set_title('Seated side section / simplified threads',loc='left',fontsize=15,color=INK)
ax.add_patch(Rectangle((0,-14),22,28,fc='#FBE7CF',ec=C['female'],lw=1.4));ax.add_patch(Rectangle((22,-12),18,24,fc='#FBE7CF',ec=C['female'],lw=1.4))
ax.add_patch(Polygon([(0,-6),(1.8,-4.2),(11.2,-4.2),(11.2,4.2),(1.8,4.2),(0,6)],fc='white',ec=C['female']))
ax.add_patch(Rectangle((-7,-14),7,28,fc='#D7EAF6',ec=C['male'],lw=1.4))
ax.add_patch(Polygon([(0,-4),(8.5,-4),(10,-3),(10,3),(8.5,4),(0,4)],fc='#D7EAF6',ec=C['male'],lw=1.2))
for z in [3,7]:
 for y in [-5,4]:ax.add_patch(Rectangle((z-.6,y),1.2,1,fc=C['male'],ec=C['male']))
ax.add_patch(Rectangle((4,2.5),2,15.5,fc='#67778C',ec=INK,lw=.8));ax.text(-11,20,'Ø2 steel lock pin',fontsize=10,color=INK)
ax.plot([-10,43],[0,0],c=MUTED,lw=.6,ls='-.')
dim(ax,(0,-17),(10,-17),'10 insertion',offset=(0,-1.5));dim(ax,(0,16),(22,16),'22',offset=(0,1.5));dim(ax,(22,16),(40,16),'18 blank',offset=(0,1.5))
ax.text(25,-3,'TOOL\nBLANK',fontsize=11,color=INK);ax.text(-12,-23,'Ø20 × 1 rear horn recess • Ø5.4 central screw relief',fontsize=10,color=MUTED)
save(fig,'02_dimensions_and_mount')

# Compact meshes for an interactive engineering view, generated from the same CAD.
meshdata={}
for name in ['male','female','female_cutaway','latch_yoke','latch_pin_envelope','rack_concept']:
 v,t=parts[name].tessellate(.12,.2)
 meshdata[name]={'v':[round(n,3) for p in v for n in p.toTuple()],'f':[int(n) for tri in t for n in tri]}
(ROOT/'viewer_meshes.json').write_text(json.dumps(meshdata,separators=(',',':')))
print('Rendered diagrams and meshes',sum(len(d['f'])//3 for d in meshdata.values()))
