"""HID keyboard-wedge scanner backend (V1).

USB barcode scanners in HID wedge mode emulate a USB keyboard: they "type"
the GTIN digits followed by an Enter keystroke into whichever input field
has focus.  No OS driver or serial port is needed.

V1 implementation
-----------------
The HID input path in V1 is handled entirely by the browser and the HTTP
layer:

1. The ``/scan`` page (``inv/web/templates/scan.html``) renders a text
   ``<input>`` with ``autofocus`` so the scanner's keystrokes land in the
   right field.
2. An HTMX ``hx-trigger="keyup[key=='Enter']"`` fires a ``POST /scan``
   with the typed GTIN.
3. JavaScript re-focuses the input after each HTMX swap so the operator can
   scan continuously without touching the keyboard.

There is no Python driver code to write for this mode — the browser IS the
driver.  This file is a stub so the package structure matches the
architecture diagram and contributors have a clear extension point if a
native HID driver (e.g. ``evdev`` on Linux) is ever needed.
"""
