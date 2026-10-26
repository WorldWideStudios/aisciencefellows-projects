// Elachistidae novel | outside CA (OR) | size_flag: database-derived, unverified | STL: novel_outside_ca/Elachistidae_novel_10.1mm.stl
// plan=moth length=10.1 mm features: spread wings 0.8 mm
// TOY model (parametric stand-in, not a replica). Canonical mesh: the matching STL.
use <toy_lib.scad>
union() {
  ellipsoid([-4.2925, 0.0000, 0.0000], [0.8711, 0.9075, 1.0090]);  // head_body
  ellipsoid([-1.7675, 0.0000, 0.0000], [1.9443, 1.1362, 1.0908]);  // thorax_body
  ellipsoid([2.5250, 0.0000, 0.0000], [2.6513, 1.2625, 1.1362]);  // abdomen_body
  plate([-1.2625, -5.3025, 0.6817], [5.5550, 9.5950, 0.8000]);  // wing_L
  plate([-1.2625, 5.3025, 0.6817], [5.5550, 9.5950, 0.8000]);  // wing_R
}
