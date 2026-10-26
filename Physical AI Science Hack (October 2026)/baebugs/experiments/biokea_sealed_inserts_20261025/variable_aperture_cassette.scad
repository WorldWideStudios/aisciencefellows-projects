/*
BioKEA Baebugs / Adjustable aperture cassette, DESIGN V1 (2026-10-25)
Mechanism: two parallel laser-cut stainless slotted screens. Top screen
translates transverse to the slots over an EMPTY lower screen, reducing the
rectangular clear-overlap width. Change ONLY at zero specimens and zero flow.
STATIC GEOMETRY ONLY. This is not a robot animation, sieve efficiency
prediction, certified seal, manufacturing release, or animal safety test.

Modes: overview, stage0, stage1, stage2, flat_base, flat_slider, flat_retainer.
Nominal values (mm) do NOT reflect hardware metrology. Both patterns exposed
for supplier review. CAD render may show small assembly clearances not feasible.
*/
$fn=40;
mode="overview";
stage=1;   // integer 0 = 3.6mm, 1 = 2.4mm, 2 = 1.2mm nominal overlap
plate=[117.2,89.2];plate_t=0.7;
slot_length=10.0; slot_width=3.6;
pitch=[14.8,10.5]; shift=[0,1.2,2.4]; 
delta=shift[stage];
carrier=[132,104]; carrier_h=15.0;
active=[90,52]; active_center=[plate[0]/2,plate[1]/2];
wiper_outline=2.0; // purely visualization, ZERO sealing qualification

// Open region needs same or smaller lower/upper slot footprint.
// Translation y only: clear width = slot_width - delta if no warping.
module slot_cut(x,y){translate([x,y,-0.2])
   cube([slot_length,slot_width,plate_t+0.4],center=false);}
module screen(){
  difference(){
    cube([plate[0],plate[1],plate_t]);
    // 6 columns by 5 rows, centered within wide solid perimeter
    for(i=[0:5],j=[0:4])
      slot_cut(12+i*pitch[0],16+j*pitch[1]);
  }
}
module frame(){
   color([0.63,0.69,0.72])
   difference(){cube([carrier[0],carrier[1],carrier_h]);
     translate([6.5,6.5,-0.1])cube([carrier[0]-13,carrier[1]-13,carrier_h+0.2]);
   }
   color([0.38,0.46,0.51])
   translate([7.4,7.4,1]) difference(){
     cube([plate[0],plate[1],2]);
     translate([5.5,5.5,-0.3])
        cube([plate[0]-11,plate[1]-11,2.6]);}
}
module upper_carriage(s){
  // no specimen may contact this slide during position change.
  translate([0,s,0]) {
    color([0.81,0.83,0.85])screen();
    color([0.57,0.65,0.69])
    translate([plate[0]-2,plate[1]/2-7,0])
       cube([19,14,plate_t]);
    // folded grip ear outside sample footprint
    color([0.67,0.73,0.76])
    translate([plate[0]+14,plate[1]/2-7,0])
       cube([3,14,13]);
  }
}
module seal(){
 // static OUTER perimeter only. Moving interface seal NOT SOLVED.
 color([0.12,0.60,0.56])
 translate([7.4,7.4,2.4])
 difference(){cube([plate[0],plate[1],1.1]);
    translate([5.5,5.5,-0.1])
      cube([plate[0]-11,plate[1]-11,1.4]);}
}
module catches(){
 // stationary upper retaining crossbars schematic, clamp load not validated
 color([0.9,0.56,0.13])
 for(y=[7,carrier[1]-11])
 translate([carrier[0]/2-20,y,7.4]) cube([40,4,3]);
}
module manual_detents(){
  // manual indexing marks; NO actuated change, no locking sensor qualified
  for(k=[0:2]) {
    color(k==stage?[0.1,0.7,0.43]:[0.82,0.72,0.24])
    translate([carrier[0]+15,carrier[1]/2-19+k*14,3])
      cylinder(h=4,d=5);
  }
}
module assembled(k){
 frame();seal();
 translate([7.4,7.4,3.6]) color([0.48,0.57,0.61]) screen();
 translate([7.4,7.4,4.35]) upper_carriage(shift[k]);
 catches();manual_detents();
}
module plot_only(type){
 if(type=="flat_base")projection(cut=false)screen();
 else if(type=="flat_slider")projection(cut=false) screen();
 else if(type=="flat_retainer")projection(cut=false)
    difference(){
       cube([plate[0],plate[1],plate_t]);
       translate([4,4,-0.1])cube([plate[0]-8,plate[1]-8,plate_t+0.2]);
    }
}
if(mode=="flat_base" || mode=="flat_slider" || mode=="flat_retainer")
  plot_only(mode);
else if(mode=="overview"){
  translate([0,0,0])assembled(0);
  translate([170,0,0])assembled(1);
  translate([340,0,0])assembled(2);
}else if(mode=="stage0")assembled(0);
else if(mode=="stage1")assembled(1);
else if(mode=="stage2")assembled(2);
