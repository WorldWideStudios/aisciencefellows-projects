// BAEBUGS-CAD-20261025 — PHOTO-INSPIRED VIRTUAL TWIN, NOT A MANUFACTURING DRAWING
// Parent source: print/bench/tower.scad + config/tower.yaml at pinned commit.
// All dimensions are provisional "MEASURE" assumptions; robot safety NOT VERIFIED.
// Includes three analog geometry references, NOT observed recovered insects.
$fn=32;
post=[38,89,580]; pitch=100; stagger=50;
tray_w=120; tray_d=90; rail_w=7; rail_h=6; frame_h=13;
module rail(x0,z,side=1) {
  color([0.83,0.67,0.45])
  for (y=[-12, post[1]+5])
    translate([x0,y,z]) cube([side==1?110:120,rail_w,rail_h]);
}
module frame(z,kind="mesh",opacity=1) {
  x=post[0]+9; y=-15;
  // Frame, six individually addressable cells.
  color(kind=="catch" ? [0.36,0.70,0.90,0.60] : [0.91,0.93,0.94,0.95])
  translate([x,y,z+rail_h])
  difference() {
    cube([tray_d,tray_w,frame_h]);
    translate([4,4,2]) cube([tray_d-8,tray_w-8,frame_h+1]);
  }
  // Orthogonal dividers, 2 rows x 3 columns.
  color([0.81,0.87,0.91])
  translate([x+4,y+tray_w/2,z+rail_h+2]) cube([tray_d-8,2,frame_h-2]);
  color([0.81,0.87,0.91])
  for (i=[1:2]) translate([x+tray_d*i/3,y+4,z+rail_h+2])
     cube([2,tray_w-8,frame_h-2]);
  // A representative flat screen; perforations are illustrative only.
  if(kind=="mesh" || kind=="coarse")
    color(kind=="mesh" ? [0.34,0.65,0.70] : [0.68,0.72,0.76])
    for (j=[0:6]) translate([x+3,y+4+j*18,z+rail_h+1])
      cube([tray_d-6,kind=="mesh"?0.9:1.5,1.0]);
  if(kind=="catch") color([0.25,0.63,0.82,0.36])
    translate([x+4,y+4,z+rail_h]) cube([tray_d-8,tray_w-8,1.5]);
  // Removable side pull-tab with clearance hole (schematic).
  color([0.89,0.89,0.91]) translate([x+tray_d,y+48,z+rail_h+3])
    difference() { cube([24,24,6]); translate([12,12,-1]) cylinder(h=9,d=9); }
}
module analogs(z) {
  // T01 simulated rice, T02 simulated chia, T03 simulated pasta ring.
  color([0.92,0.85,0.66]) translate([post[0]+38,20,z+rail_h+frame_h+3])
     scale([2.8,0.8,0.5]) sphere(d=4);
  color([0.22,0.17,0.16]) translate([post[0]+72,57,z+rail_h+frame_h+2]) sphere(d=2.4);
  color([0.90,0.64,0.10]) translate([post[0]+45,84,z+rail_h+frame_h+2])
     difference(){ cylinder(h=4,d=13);translate([0,0,-1])cylinder(h=6,d=7); }
}
color([0.41,0.24,0.17]) cube(post);
color([0.54,0.37,0.26]) translate([-140,-25,-9]) cube([330,145,9]);
for (i=[0:3]) {
  rail(-120,84+i*pitch,0);
}
for(i=[0:2]) rail(post[0],134+i*pitch,1);
frame(134,"catch");
frame(234,"mesh");
frame(334,"coarse");
analogs(334);
// Virtual camera station / rail reference, not actuator kinematics.
color([0.13,0.17,0.23]) translate([-135,-45,0]) cube([305,6,8]);
color([0.28,0.33,0.40]) translate([-30,-43,8]) cube([34,28,24]);
// Z-labelled markers: object identity is in the companion JSON ledger.
