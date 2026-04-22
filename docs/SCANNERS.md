# Scanners — open-inventory

Guide to hardware barcode scanners tested with open-inventory and
instructions for troubleshooting HID wedge input.

---

## V1 Scanner Model

V1 uses the **HID keyboard-wedge** model.  USB barcode scanners in this
mode emulate a USB keyboard: they "type" the GTIN digits followed by an
Enter keystroke into whatever input element has focus.  No OS driver, no
special software, and no Python code are required — the browser IS the
driver.

### How it works

1. The `/scan` page renders a `<input type="text" autofocus>`.
2. The scanner sends keystrokes (GTIN + Enter) to the focused field.
3. HTMX captures the Enter key and fires `POST /scan` with the typed value.
4. After the HTMX response is swapped in, JavaScript re-focuses the input
   so the operator can scan the next item immediately.

---

## Tested Scanners

The following scanners have been verified to work with open-inventory V1:

| Scanner | Interface | Notes |
|---------|-----------|-------|
| Any USB HID wedge scanner | USB-A / USB-C | Default out-of-box mode |
| Raspberry Pi + USB HID wedge | USB-A | Works identically; scanner connects to Pi's USB port |

> Most commodity barcode scanners (Netum, Symcode, Tera, Honeywell,
> Zebra entry-level) ship in HID wedge mode by default.  If yours does
> not, consult the manual — there is usually a configuration barcode to
> print and scan to switch modes.

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---------|-------------|-----|
| Scanned value not appearing in input | Input lost focus | Click the scan input to refocus; HTMX refocus should restore it automatically |
| Characters missing or garbled | Scanner baud / inter-character delay mismatch | Increase the scanner's inter-character delay via its config barcodes |
| Suffix missing (no Enter) | Scanner configured without Enter suffix | Re-configure scanner to append CR (Enter) after each scan |
| Works in isolation but not through a USB hub | Hub power | Use a powered hub or connect directly to the host USB port |
| Raspberry Pi: scanner not enumerated | USB device not detected | Run `lsusb` to confirm enumeration; try a different port |

---

## Adding a New Scanner Backend (V2+)

The `ScannerInput` protocol is defined in `inv/scan/base.py`.  Implement
it for any input method (camera, serial port, Bluetooth, network socket):

```python
from inv.scan.base import ScannerInput  # protocol placeholder

class MyScanner:
    async def read_gtin(self) -> str:
        """Block until a GTIN is available and return it."""
        ...
```

Wire the backend into the scan route or a background task.  The HTTP
layer (`POST /scan`) does not need to change — the backend can call the
same `record_scan()` service function directly.

See `docs/ARCHITECTURE.md` for the extension point map.
