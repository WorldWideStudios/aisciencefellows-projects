/*
BIOKEA / BAEBUGS -- SEALED REPLACEABLE INSERT, CAD CONCEPT V1
This is provisional fit geometry; NOT a measured tray, print-ready fabrication
document, robot simulation, watertight seal proof, or recovery performance claim.
Z is vertical. Millimeters. Robot never manipulates an UNLATCHED insert.
Modes: overview, round, slot, hex, carrier, tray, gasket, dock.
All wetted edges require finish inspection; no adhesive/Parafilm in sealing land.
*/
$fn=44;
mode="overview";
outer=[132,104]; // PHOTO-INSPIRED ONLY -- MEASURE original trays
frame_h=14;
window=[112,84];
seat=[118,90]; // interior recess
plate=[117.2,89.2]; // 0.4 mm nominal side clearance -- NOT tolerance approved
plate_t=0.8; // 316L plate candidate -- vendor must verify
z_plate=3.6;
seal_t=1.6; // free height provisional
seal_width=4.3;
gasket_compressed=0.4; // visualization only; do not interpret as actual compression
wall=7;
panel_z=0;
colors=[[0.87,0.88,0.88],[0.17,0.53,0.56],[0.95,0.54,0.15],[0.33,0.35,0.39]];

module rect_ring(w,h,innerw,innerh,t){
    difference(){
      cube([w,h,t]);
      translate([(w-innerw)/2,(h-innerh)/2,-0.1])
        cube([innerw,innerh,t+0.2]);
    }
}
module tray(){
    // Two-stage edge support / lower perimeter ledge, no inner sharp blind cavity.
    color([0.78,0.82,0.85])
      rect_ring(outer[0],outer[1],window[0],window[1],2.4);
    color([0.73,0.80,0.85])
      translate([0,0,2.4])
        rect_ring(outer[0],outer[1],seat[0],seat[1],frame_h-2.4);
    // Two M3 retention references, OUTSIDE the process window
    color([0.24,0.33,0.36])
      for (yy=[9,outer[1]-9])
        translate([outer[0]/2,yy,frame_h])
          cylinder(h=2,d=6);
}
module gasket(){
    // Continuous captive planar gasket, outside the open processing region
    color([0.08,0.53,0.55,0.90])
      translate([(outer[0]-plate[0])/2,(outer[1]-plate[1])/2,2.45])
        rect_ring(plate[0],plate[1],plate[0]-2*seal_width,plate[1]-2*seal_width,seal_t);
}
module hole_of(kind,x,y){
    if(kind=="round")
        translate([x,y,-0.3]) cylinder(h=plate_t+0.6,d=3.2,$fn=36);
    if(kind=="slot")
        translate([x,y,-0.3]) hull(){
          translate([-4.5,0,0]) cylinder(h=plate_t+0.6,d=2.4,$fn=26);
          translate([4.5,0,0]) cylinder(h=plate_t+0.6,d=2.4,$fn=26);
        }
    if(kind=="hex")
        translate([x,y,-0.3]) cylinder(h=plate_t+0.6,d=3.46,$fn=6); // about 3 mm across flats
}
module apertured_plate(kind="round"){
    // plate has continuous solid land >= 5 mm to protect gasket from apertures
    difference(){
      cube([plate[0],plate[1],plate_t]);
      if(kind=="carrier"){
        // carrier for vendor woven-mesh, clamp ring not in CAD: NO standalone mesh retention proof
        translate([8,8,-0.3])
          cube([plate[0]-16,plate[1]-16,plate_t+0.6]);
      } else if(kind=="round"){
        for(x=[9:6.2:plate[0]-9])
          for(y=[9:6.2:plate[1]-9])
             hole_of(kind,x,y);
      } else if(kind=="slot"){
        for(x=[14:16:plate[0]-14])
          for(y=[9:6.2:plate[1]-9])
             hole_of(kind,x,y);
      } else if(kind=="hex"){
        for(ix=[0:15])
          for(iy=[0:10]){
             x=9+ix*6.3 + (iy%2)*3.15;
             y=9+iy*6.4;
             if(x<plate[0]-9 && y<plate[1]-9)
               hole_of(kind,x,y);
          }
      }
    }
}
module metal_tabs(){
    // Two opposing folded stainless grip loops, outside sample-wetted aperture.
    // A human or tool handles a detached plate while the frame is STATIONARY.
    // Tabs are inaccessible to the robot during a locked inversion cycle.
    for(side=[0,1]){
        x=side==0?-13:plate[0];
        y=plate[1]/2-8;
        color([0.74,0.75,0.77])
          translate([x,y,0]) cube([13,16,plate_t]);
        color([0.78,0.80,0.81])
          translate([side==0?-13:plate[0]+10,y,0])
            cube([3,16,15]);
        color([0.78,0.80,0.81])
          translate([side==0?-13:plate[0]+8,y,12])
            cube([5,16,3]);
    }
}
module insert(kind="round",with_grips=true){
    color([0.79,0.81,0.82])
      apertured_plate(kind);
    if (with_grips) metal_tabs();
}
module seated(kind="round"){
  tray();
  gasket();
  // simplified plate is shown ABOVE the gasket at rest;
  // real compression requires calibrated stops and spring-force measurements.
  translate([(outer[0]-plate[0])/2,(outer[1]-plate[1])/2,z_plate])
    insert(kind);
}
module retainers(){
   // concept of TWO positively latched bridge clips over the metal plate only
   // No clip engagement, opening force or fastener strength has been tested.
   color([0.94,0.54,0.10])
   for (yy=[5,outer[1]-10]){
     translate([outer[0]/2-14,yy,4.5]) cube([28,5,2]);
   }
}
module drain_cassette(){
   // Contained wash/dump dock, not a robot program or pressure-certified enclosure
   color([0.24,0.55,0.70,0.32])
     translate([-14,-16,0])
       difference(){
         cube([outer[0]+28,outer[1]+32,80]);
         translate([4,4,5])
            cube([outer[0]+20,outer[1]+24,76]);
       }
   color([0.35,0.65,0.79])
     translate([-9,-11,1])
       rect_ring(outer[0]+18,outer[1]+22,outer[0]+4,outer[1]+8,4);
   // Lower secondary catch screen, separate registered fraction
   color([0.88,0.68,0.18,0.85])
     translate([0,0,8]) rect_ring(outer[0],outer[1],window[0],window[1],2);
   // cap / splash barrier is shown only as containment reference
   color([0.40,0.72,0.91,0.25])
     translate([-10,-12,79]) cube([outer[0]+20,outer[1]+24,2]);
}
module inversion_position(){
   // Static upside-down pose only. Operator/robot transition NOT simulated.
   drain_cassette();
   translate([outer[0],0,63]) rotate([0,180,0]){
     seated("round");retainers();
   }
}

module sample_tray(){
    color([0.75,0.82,0.87]) tray();
    color([0.87,0.65,0.22]) retainers();
}
if(mode=="round"||mode=="slot"||mode=="hex"||mode=="carrier"){
   // static assembled presentation (NOT a fabricated single material part)
   seated(mode);retainers();
} else if(mode=="flat_round"||mode=="flat_slot"||mode=="flat_hex"||mode=="flat_carrier"){
   // 2D cut outlines for manufacturer DFM; only the plate, NO bent tab or gasket
   projection(cut=false) apertured_plate(
     mode=="flat_round"?"round":mode=="flat_slot"?"slot":mode=="flat_hex"?"hex":"carrier");
} else if(mode=="grip_tab"){
   metal_tabs();
} else if (mode=="tray"){
   tray();
} else if (mode=="gasket"){
   gasket();
} else if (mode=="dock"){
   inversion_position();
} else {
   // four side-by-side manufacturable concepts, one separate sealed inversion dock
   translate([0,0,0]) {seated("round");retainers();}
   translate([185,0,0]) {seated("slot");retainers();}
   translate([370,0,0]) {seated("hex");retainers();}
   translate([555,0,0]) {seated("carrier");retainers();}
   translate([245,160,0]) inversion_position();
}
