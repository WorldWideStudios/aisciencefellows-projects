// Hesperiidae mean | CA museum specimens n=30: L 24.4±4.0 mm | size_flag: suspect: family mean likely wingspan, not body length | STL: california/Hesperiidae_mean_24.4mm.stl
// plan=moth length=24.4 mm features: antennae Ø0.8; spread wings 0.8 mm
// TOY model (parametric stand-in, not a replica). Canonical mesh: the matching STL.
use <toy_lib.scad>
union() {
  ellipsoid([-10.3700, 0.0000, 0.0000], [2.1045, 1.9800, 2.2960]);  // head_body
  ellipsoid([-4.2700, 0.0000, 0.0000], [4.6970, 2.7450, 2.6352]);  // thorax_body
  ellipsoid([6.1000, 0.0000, 0.0000], [6.4050, 3.0500, 2.7450]);  // abdomen_body
  rod([-11.8340, 0.0000, 0.8235], [-18.3000, -3.6600, 2.4705], 0.8000);  // antenna_L.antenna
  rod([-11.8340, 0.0000, 0.8235], [-18.3000, 3.6600, 2.4705], 0.8000);  // antenna_R.antenna
  plate([-3.0500, -12.8100, 1.6470], [13.4200, 23.1800, 0.8000]);  // wing_L
  plate([-3.0500, 12.8100, 1.6470], [13.4200, 23.1800, 0.8000]);  // wing_R
}
