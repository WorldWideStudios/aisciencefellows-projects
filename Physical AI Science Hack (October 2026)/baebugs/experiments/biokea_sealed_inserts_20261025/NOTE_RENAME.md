# Note added at merge (2026-10-25)

`test_variable_aperture.py` in this folder was renamed to `test_sealed_variable_aperture.py` because the repo already has
`tests/test_variable_aperture.py`, and pytest cannot collect two test modules with the same basename. The protocol text
(ADJUSTABLE_APERTURE_PROTOCOL.md) is left unedited; its test command now reads:

    python3 -m unittest test_capture_protocol test_sealed_variable_aperture -v
