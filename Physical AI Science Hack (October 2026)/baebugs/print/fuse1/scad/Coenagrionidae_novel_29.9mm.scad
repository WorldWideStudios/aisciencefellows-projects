// Coenagrionidae novel | outside CA (AZ, NV) | size_flag: database-derived, unverified | STL: novel_outside_ca/Coenagrionidae_novel_29.9mm.stl
// plan=damselfly length=29.9 mm features: folded wings 0.8 mm
// TOY model (parametric stand-in, not a replica). Canonical mesh: the matching STL.
use <toy_lib.scad>
union() {
  ellipsoid([-13.7540, 0.0000, 0.0000], [1.3754, 0.8676, 1.0568]);  // head_body
  ellipsoid([-10.0165, 0.0000, 0.0000], [2.7957, 1.0764, 1.1482]);  // thorax_body
  ellipsoid([3.7375, 0.0000, 0.0000], [11.7731, 1.1960, 1.1960]);  // abdomen_body
  plate([-1.0465, -0.4605, 1.2438], [22.4250, 1.3156, 0.8000]);  // wing_L
  plate([-1.0465, 0.4605, 1.2438], [22.4250, 1.3156, 0.8000]);  // wing_R
}
