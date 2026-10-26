// Elachistidae novel | outside CA (OR) | size_flag: database-derived, unverified | STL: novel_outside_ca/Elachistidae_novel_8.4mm.stl
// plan=moth length=8.4 mm features: spread wings 0.8 mm
// TOY model (parametric stand-in, not a replica). Canonical mesh: the matching STL.
use <toy_lib.scad>
union() {
  ellipsoid([-3.5700, 0.0000, 0.0000], [0.7245, 0.7800, 0.8560]);  // head_body
  ellipsoid([-1.4700, 0.0000, 0.0000], [1.6170, 0.9450, 0.9072]);  // thorax_body
  ellipsoid([2.1000, 0.0000, 0.0000], [2.2050, 1.0500, 0.9450]);  // abdomen_body
  plate([-1.0500, -4.4100, 0.5670], [4.6200, 7.9800, 0.8000]);  // wing_L
  plate([-1.0500, 4.4100, 0.5670], [4.6200, 7.9800, 0.8000]);  // wing_R
}
