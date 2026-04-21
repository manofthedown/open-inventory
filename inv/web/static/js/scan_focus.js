// Keep scan input focused
document.addEventListener("DOMContentLoaded", () => {
  const scanInput = document.getElementById("scan-input");
  if (scanInput) {
    scanInput.focus();
    // Re-focus after any HTMX partial update
    document.addEventListener("htmx:afterSwap", () => {
      scanInput.focus();
    });
  }
});
