"""BioKEA sample-prep line translated onto an Opentrons Flex (simulation-checked, not hardware-tested).

Module mapping (BioKEA -> Flex):
  1 BugSorter        -> baebugs mini trommel (D2, motor run by an external controller) and the
                        mini sieve stack on the Heater-Shaker (gentle shake = vortexer)
  2 BugDisperser     -> sieve ring on the Heater-Shaker spreading specimens for imaging
  3 BugPicker        -> external arm or suction picker, via the hand-off carrier (B2)
  4 Enzyme dispenser -> Flex 1-channel 1000 uL pipette (lysis buffer + proteinase K)
  5 Turnstile incub. -> second Heater-Shaker (D3) at 56 C, slow shake (non-destructive whole-body soak;
                        the exoskeleton is kept as the voucher)
Every physical motion outside the Flex (trommel motor, external arm, camera, entomologist) is a
pause: a person or a controller confirms it, and that confirmation is the hand-off record.
Custom labware: opentrons/labware/*.json (load with opentrons_simulate -L opentrons/labware).
"""
from opentrons import protocol_api

metadata = {"protocolName": "baebugs BioKEA line on Flex (sort -> image -> pick -> lyse -> incubate)",
            "author": "baebugs", "description": "Deck translation of the BioKEA Track A modules; simulation only"}
requirements = {"robotType": "Flex", "apiLevel": "2.20"}

N_SPECIMENS = 8          # one specimen per well (column 1)
SHAKE_SIEVE_RPM = 200    # Heater-Shaker minimum; gentle for wings and legs
SHAKE_SIEVE_S = 60
SOAK_C = 56              # non-destructive proteinase K soak (common practice; check your protocol)
SOAK_MIN = 60
LYSIS_UL = 200


def run(protocol: protocol_api.ProtocolContext):
    hs = protocol.load_module("heaterShakerModuleV1", "D1")              # module 2: disperser / vortexer
    hs_adapter = hs.load_adapter("opentrons_universal_flat_adapter")
    inc = protocol.load_module("heaterShakerModuleV1", "D3")             # module 5: incubator
    inc_adapter = inc.load_adapter("opentrons_96_deep_well_adapter")
    trommel = protocol.load_labware("baebugs_mini_trommel_4bin", "D2", namespace="custom_beta")
    sieve = protocol.load_labware("baebugs_sieve_adapter_50mm", "C2", namespace="custom_beta")
    handoff = protocol.load_labware("baebugs_handoff_plate", "B2", namespace="custom_beta")
    plate = protocol.load_labware("nest_96_wellplate_2ml_deep", "B1")
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", "C1")
    tips = protocol.load_labware("opentrons_flex_96_tiprack_1000ul", "A2")
    protocol.load_trash_bin("A3")
    p1000 = protocol.load_instrument("flex_1channel_1000", "left", tip_racks=[tips])
    lysis = protocol.define_liquid("lysis buffer + proteinase K", "non-destructive whole-body soak", "#4a90a4")
    reservoir["A1"].load_liquid(lysis, 12000)

    # 1 BugSorter: mini trommel fractions land in bins A1 (1.5 mm) .. A4 (oversize)
    protocol.comment("STEP 1 sort: load sample into the mini trommel feed (D2)")
    protocol.pause("Run the trommel motor (external controller) until the drum is clear; confirm to continue")

    # 2 BugDisperser: sieve stack on the Heater-Shaker, gentle shake spreads specimens for imaging
    hs.open_labware_latch()
    protocol.move_labware(sieve, hs_adapter, use_gripper=True)
    hs.close_labware_latch()
    hs.set_and_wait_for_shake_speed(SHAKE_SIEVE_RPM)
    protocol.delay(seconds=SHAKE_SIEVE_S)
    hs.deactivate_shaker()
    hs.open_labware_latch()
    protocol.move_labware(sieve, "C2", use_gripper=True)
    protocol.pause("STEP 2 image: camera images each ring; vision gate flags novel specimens for the entomologist")

    # 3 BugPicker: one specimen per well via the hand-off carrier (external arm or suction)
    protocol.pause(f"STEP 3 pick: external arm / suction places {N_SPECIMENS} specimens into column 1 of the "
                   f"deep-well plate (B1), using the hand-off carrier at B2 ({handoff.load_name})")

    # 4 Enzyme dispenser: lysis buffer into every specimen well
    p1000.distribute(LYSIS_UL, reservoir["A1"], [plate.wells()[i] for i in range(N_SPECIMENS)], new_tip="once")

    # 5 Incubator: gentle 56 C soak on the Heater-Shaker; exoskeleton stays intact as the voucher
    inc.open_labware_latch()
    protocol.move_labware(plate, inc_adapter, use_gripper=True)
    inc.close_labware_latch()
    inc.set_and_wait_for_temperature(SOAK_C)
    inc.set_and_wait_for_shake_speed(300)
    protocol.delay(minutes=SOAK_MIN)
    inc.deactivate_shaker(); inc.deactivate_heater()
    inc.open_labware_latch()
    protocol.move_labware(plate, "B1", use_gripper=True)
    protocol.comment("Lysate -> DNA cleanup and barcoding; specimens (exoskeleton, wings, legs) kept as vouchers")
