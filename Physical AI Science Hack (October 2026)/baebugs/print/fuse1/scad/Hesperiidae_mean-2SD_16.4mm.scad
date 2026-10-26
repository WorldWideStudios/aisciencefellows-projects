// Hesperiidae mean-2SD | CA museum specimens n=30: L 24.4±4.0 mm | size_flag: suspect: family mean likely wingspan, not body length | STL: california/Hesperiidae_mean-2SD_16.4mm.stl
// plan=moth length=16.4 mm features: antennae Ø0.8; spread wings 0.8 mm
// TOY model (parametric stand-in, not a replica). Canonical mesh: the matching STL.
use <toy_lib.scad>
union() {
  ellipsoid([-6.9700, 0.0000, 0.0000], [1.4145, 1.3800, 1.5760]);  // head_body
  ellipsoid([-2.8700, 0.0000, 0.0000], [3.1570, 1.8450, 1.7712]);  // thorax_body
  ellipsoid([4.1000, 0.0000, 0.0000], [4.3050, 2.0500, 1.8450]);  // abdomen_body
  rod([-7.9540, 0.0000, 0.5535], [-12.3000, -2.4600, 1.6605], 0.8000);  // antenna_L.antenna
  rod([-7.9540, 0.0000, 0.5535], [-12.3000, 2.4600, 1.6605], 0.8000);  // antenna_R.antenna
  plate([-2.0500, -8.6100, 1.1070], [9.0200, 15.5800, 0.8000]);  // wing_L
  plate([-2.0500, 8.6100, 1.1070], [9.0200, 15.5800, 0.8000]);  // wing_R
}
