---
status: verifying
created: 2026-04-19T10:00:00Z
updated: 2026-04-19T10:45:00Z
trigger: VTK crashes when running via SSH X11 forwarding (DISPLAY=localhost:12.0) with QUICKICE_FORCE_VTK=true
---

## Current Focus
next_action: verify full application with SSH X11
fix_applied: Configured OpenGL to use Mesa GLX for remote displays in _configure_opengl_for_remote()
verification_test: Run quickice.gui with QUICKICE_FORCE_VTK=true via SSH X11

## Symptoms
expected: QVTKRenderWindowInteractor initializes and renders VTK viewer over SSH X11
actual: segmentation fault (core dumped) during QVTKRenderWindowInteractor.__init__() at line 362
errors:
  - " segmentation fault (core dumped)"
  - dmesg: segfault at 0 (null pointer dereference)
reproduction:
  1. SSH -Y to this machine (DISPLAY=localhost:12.0)
  2. export QUICKICE_FORCE_VTK=true
  3. python -m quickice.gui

## Resolution
root_cause: NVIDIA GLX library (libGLX_nvidia.so.0) crashes with indirect X11 rendering. The NVIDIA driver assumes direct rendering is always available and crashes when trying to use indirect rendering paths over SSH X11 forwarding.
fix: Added _configure_opengl_for_remote() function that detects remote displays and forces Mesa GLX (__GLX_VENDOR_LIBRARY_NAME=mesa) instead of NVIDIA GLX
files_changed:
  - quickice/gui/main_window.py: Added _configure_opengl_for_remote() and call in run_app()
verification: VTK/Qt integration now works over SSH X11 with QUICKICE_FORCE_VTK=true

## Evidence
- timestamp: 2026-04-19T10:05:00Z
  checked: OpenGL/glxinfo output
  found: "direct rendering: No" - indirect X11 rendering is being used
- timestamp: 2026-04-19T10:15:00Z
  checked: DISPLAY=:0 (local)
  found: VTK works with local display (:0), no crash
  implication: Problem is specific to SSH X11 forwarding mode
- timestamp: 2026-04-19T10:20:00Z
  checked: EGL availability
  found: EGL library available, VTK can use EGL-mode rendering
- timestamp: 2026-04-19T10:40:00Z
  checked: __GLX_VENDOR_LIBRARY_NAME=mesa
  found: Setting this environment variable forces Mesa GLX which handles indirect rendering
  implication: Solution found
- timestamp: 2026-04-19T10:45:00Z
  checked: Full VTK/Qt test with remote display
  found: QVTKRenderWindowInteractor creates successfully with __GLX_VENDOR_LIBRARY_NAME=mesa
  verification: Fix verified working