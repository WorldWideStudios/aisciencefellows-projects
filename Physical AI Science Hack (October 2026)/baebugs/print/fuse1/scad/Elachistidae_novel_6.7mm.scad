// Elachistidae novel | outside CA (OR) | size_flag: database-derived, unverified | STL: novel_outside_ca/Elachistidae_novel_6.7mm.stl
// plan=moth length=6.7 mm features: body only
// TOY model (parametric stand-in, not a replica). Canonical mesh: the matching STL.
use <toy_lib.scad>
union() {
  ellipsoid([-2.8475, 0.0000, 0.0000], [0.5779, 0.6525, 0.7030]);  // head_body
  ellipsoid([-1.1725, 0.0000, 0.0000], [1.2897, 0.7538, 0.7236]);  // thorax_body
  ellipsoid([1.6750, 0.0000, 0.0000], [1.7588, 0.8375, 0.7538]);  // abdomen_body
}
