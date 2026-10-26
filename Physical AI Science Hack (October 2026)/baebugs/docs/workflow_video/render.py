"""Rebuild a 30s comparison from OpenSCAD meshes. No hardware connection."""
from pathlib import Path
import subprocess, re, json, hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from PIL import Image, ImageDraw, ImageFont
D=Path(__file__).resolve().parent
F=D/'frames';F.mkdir(exist_ok=True)
font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
def ft(n):return ImageFont.truetype(font,n)
stages=[('01  INTAKE + SEPARATION','BioKEA: BugSorter and BugDisperser precede picking.','Addition: capture scale, candidate image and fraction identity.'),('02  PICKER READY','BioKEA: plate staged at BugPicker.','Addition: review detections, overlap and specimen-to-well map.'),('03  ARM TRANSFER','BioKEA documented shuttle: pick plate and transfer to imager.','Addition: proposed preflight and before/after handoff evidence.'),('04  IMAGE / SCAN','BioKEA documented shuttle invokes plate-reader scan.','Addition: bind image, model output and human decision separately.'),('05  ARM RETURN','BioKEA documented shuttle returns plate to BugPicker.','Addition: verify destination and record recovery or disagreement.'),('06  DOWNSTREAM','BioKEA line includes dispenser and incubator (not this shuttle).','Addition: draft protocol links; chemistry/temperature need sensors.')]
# Two poses per stage. This is illustrative keyframe animation, not motion planning.
for i in range(12):
 stage=i//2;u=(i%2)*.8+.1
 out=Image.new('RGB',(1280,900),'#101e28');dr=ImageDraw.Draw(out)
 dr.text((35,18),'BaeBugs | original workflow + proposed integration',font=ft(29),fill='white')
 dr.text((35,59),'OPENSCAD ANIMATION  /  NOT HARDWARE FOOTAGE  /  GEOMETRY NOT MEASURED',font=ft(17),fill='#ffc976')
 for lane in range(2):
  mesh=F/f'mesh_{i:02}_{lane}.stl'
  subprocess.run(['openscad','-o',str(mesh),'-D',f'stage={stage}','-D',f'u={u}','-D',f'overlay={lane}',str(D/'workcell.scad')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  vals=np.array(re.findall(r'vertex\s+([-+\deE.]+)\s+([-+\deE.]+)\s+([-+\deE.]+)',mesh.read_text()),float).reshape(-1,3,3)
  fig=plt.figure(figsize=(12.8,3.25),dpi=100,facecolor='#101e28');ax=fig.add_subplot(projection='3d');ax.set_facecolor('#101e28')
  coll=Poly3DCollection(vals,facecolors=('#a8b7c2' if lane==0 else '#64c9b9'),edgecolors='#314858',linewidths=.15)
  ax.add_collection3d(coll);ax.set_xlim(-15,290);ax.set_ylim(-15,145);ax.set_zlim(-10,100);ax.set_box_aspect((3,1.6,1.1));ax.view_init(elev=27,azim=-62);ax.set_axis_off();fig.subplots_adjust(0,0,1,1)
  p=F/f'view_{i:02}_{lane}.png';fig.savefig(p,facecolor=fig.get_facecolor());plt.close(fig)
  y=105+lane*360;out.paste(Image.open(p).convert('RGB').crop((380,80,960,310)).resize((1000,280)),(140,y+30));dr=ImageDraw.Draw(out)
  dr.text((35,y),'BIOKEA BASELINE - documented sequence' if lane==0 else 'BAEBUGS ADDITIONS - proposed physical integration',font=ft(22),fill='white' if lane==0 else '#7df2d4')
  dr.text((35,y+310),stages[stage][lane+1],font=ft(19),fill='#e1e8ee')
 dr.text((35,838),stages[stage][0],font=ft(24),fill='#ffc976')
 dr.text((35,876),'No performance / novelty validation. Cameras shown are proposed. No robot commands generated.',font=ft(15),fill='#b4c4cf')
 out.save(F/f'frame_{i:02}.png');print('RUNNING',i+1,'/12',flush=True)
subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate','2/5','-i',str(F/'frame_%02d.png'),'-vf','fps=24','-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart',str(D/'biokea_vs_baebugs.mp4')],check=True)
print('PASS video rendered',flush=True)
