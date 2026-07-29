# Neuron Lab Automation — Zeon

## Demo holder-removal anchor path

Use this ordered JSON list with the `move_arm_to_anchor` skill:

```json
[
  "holder_position_0",
  "holder_position_move_open_0",
  "grab_holder_1",
  "grab_holder_up_2",
  "grab_holder_grasped_back_3",
  "grab_holder_set_down_4",
  "grab_holder_release_5"
]
```

The anchors are defined on the `openshelf` object and are used by
`demo_workflow` with `demo_anchored_shelf`.
