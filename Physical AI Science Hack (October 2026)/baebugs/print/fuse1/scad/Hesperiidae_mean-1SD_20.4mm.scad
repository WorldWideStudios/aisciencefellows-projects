// Hesperiidae mean-1SD | CA museum specimens n=30: L 24.4±4.0 mm | size_flag: suspect: family mean likely wingspan, not body length | STL: california/Hesperiidae_mean-1SD_20.4mm.stl
// plan=moth length=20.4 mm features: antennae Ø0.8; spread wings 0.8 mm
// TOY model (parametric stand-in, not a replica). Canonical mesh: the matching STL.
use <toy_lib.scad>
union() {
  ellipsoid([-8.6700, 0.0000, 0.0000], [1.7595, 1.6800, 1.9360]);  // head_body
  ellipsoid([-3.5700, 0.0000, 0.0000], [3.9270, 2.2950, 2.2032]);  // thorax_body
  ellipsoid([5.1000, 0.0000, 0.0000], [5.3550, 2.5500, 2.2950]);  // abdomen_body
  rod([-9.8940, 0.0000, 0.6885], [-15.3000, -3.0600, 2.0655], 0.8000);  // antenna_L.antenna
  rod([-9.8940, 0.0000, 0.6885], [-15.3000, 3.0600, 2.0655], 0.8000);  // antenna_R.antenna
  plate([-2.5500, -10.7100, 1.3770], [11.2200, 19.3800, 0.8000]);  // wing_L
  plate([-2.5500, 10.7100, 1.3770], [11.2200, 19.3800, 0.8000]);  // wing_R
}
