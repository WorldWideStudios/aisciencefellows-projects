// Andrenidae (Perdita sp.) novel | outside CA (AZ) | size_flag: database-derived, unverified | STL: novel_outside_ca/Andrenidae_Perdita_sp_novel_3.6mm.stl
// plan=bee length=3.6 mm features: body only
// TOY model (parametric stand-in, not a replica). Canonical mesh: the matching STL.
use <toy_lib.scad>
union() {
  ellipsoid([-1.4760, 0.0000, 0.0000], [0.3726, 0.6036, 0.6443]);  // head_body
  ellipsoid([-0.5760, 0.0000, 0.0000], [0.6336, 0.6804, 0.6532]);  // thorax_body
  ellipsoid([0.9000, 0.0000, 0.0000], [0.9450, 0.7560, 0.6804]);  // abdomen_body
}
