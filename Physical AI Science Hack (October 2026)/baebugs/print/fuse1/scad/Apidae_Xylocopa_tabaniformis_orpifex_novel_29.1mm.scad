// Apidae (Xylocopa tabaniformis orpifex) novel | outside CA (OR) | size_flag: suspect: 29.1 mm larger than typical for this carpenter bee | STL: novel_outside_ca/Apidae_Xylocopa_tabaniformis_orpifex_novel_29.1mm.stl
// plan=bee length=29.1 mm features: 6 legs Ø1.10; antennae Ø0.8; folded wings 0.8 mm
// TOY model (parametric stand-in, not a replica). Canonical mesh: the matching STL.
use <toy_lib.scad>
union() {
  ellipsoid([-11.9310, 0.0000, 0.0000], [3.0118, 3.8166, 4.4999]);  // head_body
  ellipsoid([-4.6560, 0.0000, 0.0000], [5.1216, 5.4999, 5.2799]);  // thorax_body
  ellipsoid([7.2750, 0.0000, 0.0000], [7.6388, 6.1110, 5.4999]);  // abdomen_body
  rod([-7.4496, -3.0555, -1.1000], [-9.6321, -5.0416, -1.1000], 1.1000);  // leg_1L.femur
  rod([-9.6321, -5.0416, -1.1000], [-12.2511, -9.1665, -4.9499], 1.1000);  // leg_1L.tibia
  rod([-7.4496, 3.0555, -1.1000], [-9.6321, 5.0416, -1.1000], 1.1000);  // leg_1R.femur
  rod([-9.6321, 5.0416, -1.1000], [-12.2511, 9.1665, -4.9499], 1.1000);  // leg_1R.tibia
  rod([-4.6560, -3.0555, -1.1000], [-4.6560, -5.0416, -1.1000], 1.1000);  // leg_2L.femur
  rod([-4.6560, -5.0416, -1.1000], [-4.6560, -9.1665, -4.9499], 1.1000);  // leg_2L.tibia
  rod([-4.6560, 3.0555, -1.1000], [-4.6560, 5.0416, -1.1000], 1.1000);  // leg_2R.femur
  rod([-4.6560, 5.0416, -1.1000], [-4.6560, 9.1665, -4.9499], 1.1000);  // leg_2R.tibia
  rod([-1.8624, -3.0555, -1.1000], [0.3201, -5.0416, -1.1000], 1.1000);  // leg_3L.femur
  rod([0.3201, -5.0416, -1.1000], [7.3041, -9.1665, -4.9499], 1.1000);  // leg_3L.tibia
  rod([-1.8624, 3.0555, -1.1000], [0.3201, 5.0416, -1.1000], 1.1000);  // leg_3R.femur
  rod([0.3201, 5.0416, -1.1000], [7.3041, 9.1665, -4.9499], 1.1000);  // leg_3R.tibia
  rod([-14.0262, 0.0000, 1.6500], [-21.8250, -7.3332, 4.9499], 0.8000);  // antenna_L.antenna
  rod([-14.0262, 0.0000, 1.6500], [-21.8250, 7.3332, 4.9499], 0.8000);  // antenna_R.antenna
  plate([4.0740, -2.3527, 5.7199], [21.8250, 6.7221, 0.8000]);  // wing_L
  plate([4.0740, 2.3527, 5.7199], [21.8250, 6.7221, 0.8000]);  // wing_R
}
