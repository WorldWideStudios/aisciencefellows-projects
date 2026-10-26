// Formicidae mean-1SD | CA museum specimens n=26: L 6.9±2.2 mm | size_flag: database-derived, unverified | STL: california/Formicidae_mean-1SD_4.7mm.stl
// plan=ant length=4.7 mm features: body only
// TOY model (parametric stand-in, not a replica). Canonical mesh: the matching STL.
use <toy_lib.scad>
union() {
  ellipsoid([-1.7625, 0.0000, 0.0000], [0.6756, 0.5025, 0.5230]);  // head_body
  ellipsoid([-0.3525, 0.0000, 0.0000], [0.9048, 0.5288, 0.5076]);  // thorax_body
  ellipsoid([1.4100, 0.0000, 0.0000], [0.9870, 0.5875, 0.5288]);  // abdomen_body
}
