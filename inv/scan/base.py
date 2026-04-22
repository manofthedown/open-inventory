"""Scanner input protocol.

Defines the ``ScannerInput`` protocol that all scanner backends must satisfy.
V1 ships one concrete backend — the HID keyboard-wedge (``inv.scan.hid``) —
which receives GTIN input via the browser's ``<input>`` element and an HTMX
POST.  Additional backends (e.g. camera, serial port) can be added in future
milestones by implementing this protocol without touching core scan logic.

Protocol contract
-----------------
A ``ScannerInput`` implementation is not yet wired into the runtime; V1
scanning flows entirely through the HTTP layer (``/scan`` route → service
layer).  This module is a slot-holder so the architecture is explicit and
contributors know where to add new input methods.
"""
