// Andrenidae (Andrena prunorum) novel | outside CA (OR) | size_flag: suspect: 20.1 mm far larger than typical for this mining bee | STL: novel_outside_ca/Andrenidae_Andrena_prunorum_novel_20.1mm.stl
// plan=bee length=20.1 mm features: 6 legs Ø0.80; antennae Ø0.8; folded wings 0.8 mm
// TOY model (parametric stand-in, not a replica). Canonical mesh: the matching STL.
use <toy_lib.scad>
union() {
  ellipsoid([-8.2410, 0.0000, 0.0000], [2.0804, 2.6826, 3.1391]);  // head_body
  ellipsoid([-3.2160, 0.0000, 0.0000], [3.5376, 3.7989, 3.6469]);  // thorax_body
  ellipsoid([5.0250, 0.0000, 0.0000], [5.2763, 4.2210, 3.7989]);  // abdomen_body
  rod([-5.1456, -2.1105, -0.7598], [-6.6531, -3.4823, -0.7598], 0.8000);  // leg_1L.femur
  rod([-6.6531, -3.4823, -0.7598], [-8.4621, -6.3315, -3.4190], 0.8000);  // leg_1L.tibia
  rod([-5.1456, 2.1105, -0.7598], [-6.6531, 3.4823, -0.7598], 0.8000);  // leg_1R.femur
  rod([-6.6531, 3.4823, -0.7598], [-8.4621, 6.3315, -3.4190], 0.8000);  // leg_1R.tibia
  rod([-3.2160, -2.1105, -0.7598], [-3.2160, -3.4823, -0.7598], 0.8000);  // leg_2L.femur
  rod([-3.2160, -3.4823, -0.7598], [-3.2160, -6.3315, -3.4190], 0.8000);  // leg_2L.tibia
  rod([-3.2160, 2.1105, -0.7598], [-3.2160, 3.4823, -0.7598], 0.8000);  // leg_2R.femur
  rod([-3.2160, 3.4823, -0.7598], [-3.2160, 6.3315, -3.4190], 0.8000);  // leg_2R.tibia
  rod([-1.2864, -2.1105, -0.7598], [0.2211, -3.4823, -0.7598], 0.8000);  // leg_3L.femur
  rod([0.2211, -3.4823, -0.7598], [5.0451, -6.3315, -3.4190], 0.8000);  // leg_3L.tibia
  rod([-1.2864, 2.1105, -0.7598], [0.2211, 3.4823, -0.7598], 0.8000);  // leg_3R.femur
  rod([0.2211, 3.4823, -0.7598], [5.0451, 6.3315, -3.4190], 0.8000);  // leg_3R.tibia
  rod([-9.6882, 0.0000, 1.1397], [-15.0750, -5.0652, 3.4190], 0.8000);  // antenna_L.antenna
  rod([-9.6882, 0.0000, 1.1397], [-15.0750, 5.0652, 3.4190], 0.8000);  // antenna_R.antenna
  plate([2.8140, -1.6251, 3.9509], [15.0750, 4.6431, 0.8000]);  // wing_L
  plate([2.8140, 1.6251, 3.9509], [15.0750, 4.6431, 0.8000]);  // wing_R
}
