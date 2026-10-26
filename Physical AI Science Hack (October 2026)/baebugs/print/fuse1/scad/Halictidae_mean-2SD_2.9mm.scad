// Halictidae mean-2SD | CA museum specimens n=308: L 9.9±3.5 mm | size_flag: suspect: family mean runs large for sweat bees | STL: california/Halictidae_mean-2SD_2.9mm.stl
// plan=bee length=2.9 mm features: body only
// TOY model (parametric stand-in, not a replica). Canonical mesh: the matching STL.
use <toy_lib.scad>
union() {
  ellipsoid([-1.1890, 0.0000, 0.0000], [0.3001, 0.5154, 0.5385]);  // head_body
  ellipsoid([-0.4640, 0.0000, 0.0000], [0.5104, 0.5481, 0.5262]);  // thorax_body
  ellipsoid([0.7250, 0.0000, 0.0000], [0.7612, 0.6090, 0.5481]);  // abdomen_body
}
