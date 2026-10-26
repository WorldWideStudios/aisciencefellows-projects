# Generation 3 PC Control implementation evidence

Device reported by operator on 2026-09-10: VIAFLO 125 µL single channel,
SN 07064070, generation 3, firmware 5.10, hardware 5, display 3, bootloader
4.00, spinner 2.01, ComModule BTM411 firmware 16.01.03.00, flash type 1.
Mode: PC Control (ComM). Bluetooth address 00-16-a4-4c-9a-ac, channel 1.

Manufacturer confirms PC Control (ComM) is external control through the module:
https://www.integra-biosciences.com/sites/default/files/documents/161950_V14_OI_VIAFLO_VOYAGER_Pipettes_EN.pdf
(page 23). API packages are available through laboratory integration:
https://www.integra-biosciences.com/global/en/support/laboratory-integration

Interoperability reference: GormleyLab's published pipette liquid handler,
`Pipette SDL Software/resources/RemoteControl.dll` and
`Pipette SDL Software/src/liquidhandler.py`:
https://github.com/GormleyLab/Pipette-Liquid-Handler

Reference repository commit: `e46f3030041959781fbb59989735f1ae847ba244`.
DLL SHA-256: `14fb14bd00b333d87cdacb10678c2bdf005351ceddfb05ae738c082fe6658211`.

Inspected DLL metadata and method IL with monodis, without executing the DLL.
The Python implementation uses the following protocol facts, not the DLL runtime:

- RemoteCtrlProtocol.SendMessage: eight-byte header (big-endian total length,
  additive checksum, 16-bit sequence, zero reserved byte, 16-bit command).
  Escape 02/03/1b with prefix 1b, delimit with one STX and one ETX.
- RemoteCtrl.onAnswerReceived: response body starts with a **16-bit** status,
  0 accepted, 1 unknown message, 2 value out of range, 3 hardware error,
  4 command not accepted.
- GetInfo = 1, empty request. Twenty-byte response: firmware bytes 10,11;
  hardware byte 13; binary serial bytes 14–17; model code bytes 18–19.
- GetActionStatus = 2, empty request. Fourteen-byte response: state uint16 at
  10, hardware error uint16 at 12. States 0 ready, 1 wait blow-in, 2 wait RUN,
  3 busy, 4 not homed, 5 user abort.
- SetAction = 5. Body is action u8, speed u8, volume u16 big endian, mix cycles
  u8, RUN confirmation u8, twenty ASCII message bytes, spacing u16 big endian.
  Ten-byte acknowledgment has status only. Poll GetActionStatus for completion.
- Actions: 1 aspirate, 7 dispense without blowout, 4 purge. Implementation
  restricts itself to these. No automatic home, blowout, calibration, or reset.
- The lab's liquidhandler.py explicitly multiplies µL by ten before passing
  volume to PipetteAPI. This is commanded volume, not measured volume.
- **Message 4 is SetCalibrationFactor in this API, not legacy piston action.**
  The new GUI imports pc_control.Controller and never sends message 4.

Captured real GetInfo packet:
`00148f00010000010000050a0005006bca06000c`.
Length, checksum, sequence, command and zero status validate. Firmware 5.10,
hardware 5 and serial 07064070 match operator information exactly.

The DLL model enum maps 12 to Voyager 8ch 300 and 20 to SC125, whereas the
operator's single-channel 125 reports 12. Do not silently apply that enum.
The implementation gates motion on the exact observed serial/firmware/hardware/
raw-model tuple and uses the operator-confirmed 125 µL capacity. Other devices
must get their own verified profile. This does not establish broad compatibility.

Volume tracking starts unknown at each connection. Operator confirmation of
empty initializes zero. Acknowledged actions followed by Ready update the
ledger; it is not piston telemetry. Any failed action disconnects and invalidates
the ledger; no motion retry or compensating dispense is issued.

Software checks cover real fragmented identity, 16-bit errors, read-only
connection, volume limits, busy/hardware failures and no retry after timeout.
Actual motor behavior and liquid-volume accuracy still require physical tests.

## Live verification 2026-09-10

Read-only connection: `logs/20260910-115613-179783.jsonl` validated the
expected identity and Ready with hardware error 0.

After operator explicitly confirmed empty and out of liquid,
`logs/20260910-115728-580664.jsonl` recorded a 5 µL dry cycle at speed 1:
SetAction 1 (aspirate), accepted, Busy → Ready; SetAction 7 (dispense without
blowout), accepted, Busy → Ready. No errors or retries. Tracked volume 0 µL.
The operator requested a second cycle, recorded in
`logs/20260910-115825-745353.jsonl`, and explicitly confirmed seeing/hearing
motion afterward. No gravimetric volume check was performed.
