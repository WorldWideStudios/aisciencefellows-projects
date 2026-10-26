// Hesperiidae mean+1SD | CA museum specimens n=30: L 24.4±4.0 mm | size_flag: suspect: family mean likely wingspan, not body length | STL: california/Hesperiidae_mean+1SD_28.4mm.stl
// plan=moth length=28.4 mm features: antennae Ø0.8; spread wings 0.8 mm
// TOY model (parametric stand-in, not a replica). Canonical mesh: the matching STL.
use <toy_lib.scad>
union() {
  ellipsoid([-12.0700, 0.0000, 0.0000], [2.4495, 2.2800, 2.6560]);  // head_body
  ellipsoid([-4.9700, 0.0000, 0.0000], [5.4670, 3.1950, 3.0672]);  // thorax_body
  ellipsoid([7.1000, 0.0000, 0.0000], [7.4550, 3.5500, 3.1950]);  // abdomen_body
  rod([-13.7740, 0.0000, 0.9585], [-21.3000, -4.2600, 2.8755], 0.8000);  // antenna_L.antenna
  rod([-13.7740, 0.0000, 0.9585], [-21.3000, 4.2600, 2.8755], 0.8000);  // antenna_R.antenna
  plate([-3.5500, -14.9100, 1.9170], [15.6200, 26.9800, 0.8000]);  // wing_L
  plate([-3.5500, 14.9100, 1.9170], [15.6200, 26.9800, 0.8000]);  // wing_R
}
