// Illustrative geometry, original scene; not measured BioKEA/xArm CAD.
// stage=0..5, u=0..1, overlay=0/1.
stage=0; u=0; overlay=0; $fn=16;
module block(p,s,c){color(c) translate(p) cube(s);}
module plate(p){block(p,[28,20,4],"gold");for(x=[3:4:25],y=[3:3:17]) color("black")translate(p+[x,y,4])cylinder(h=1,r=.7);}
module link(a,b,r,c){color(c)hull(){translate(a)sphere(r);translate(b)sphere(r);}}
block([-10,-10,-7],[300,150,7],[.16,.20,.23]);
// Baseline instruments: sorter/disperser, BugPicker, imager, dispenser/incubator.
for(i=[0:4]){block([i*56,78,0],[44,44,6],[.65,.69,.71]);}
for(z=[10,22,34]) block([0,80,z],[40,38,3],[.36,.58,.63]);
block([58,82,7],[36,32,4],[.35,.65,.8]);
block([112,80,7],[38,38,18],[.38,.45,.55]);
block([168,80,7],[40,38,30],[.5,.55,.58]);
block([224,80,7],[40,38,42],[.55,.4,.3]);
// Arm shuttles plate between picker (x=70) and imager (x=126).
f=stage<2?0:stage==2?u:stage==3?1:stage==4?1-u:0;
x=70+56*f; z=stage==2||stage==4?43+12*sin(u*180):25;
block([80,15,0],[28,28,10],[.75,.76,.78]);
a=[94,29,12]; b=[94,45,72]; c=[x,82,z+16];
link(a,b,6,[.8,.82,.84]);link(b,c,5,[.85,.86,.88]);link(c,[x,91,z+4],3,"silver");
plate([x-14,82,z]);
if(overlay){
// Cyan cameras and inspection cones are proposed additions, not observed devices.
for(i=[0:4]){block([i*56+15,125,55],[15,10,9],[0,.8,.75]);link([i*56+22,128,55],[i*56+22,100,12],.6,[0,.8,.75]);}
color([0,1,.65])translate([stage%5*56+22,100,8])difference(){cylinder(h=1,r=25);cylinder(h=2,r=24);}
}
