# Packaging icons

One app icon (navy tile, white star, red flag bar; same in light and dark) for package recipes. Derived from `brand/icons/platforms` by `brand/src/build_packaging_icons.py`. Alt text: "Free My ID app icon".

| File | Size | Use |
|---|---|---|
| `freemyid.svg` | scalable | Flatpak (preferred, `scalable/apps/`), AUR/Linux hicolor, AppStream |
| `freemyid-16.png` ... `freemyid-512.png` | 16, 32, 48, 64, 128, 256, 512 px | Linux hicolor sizes. Flatpak needs 128 and 64 at minimum if no SVG. AUR: install 48/64 (pixmaps) or all under `hicolor/<N>x<N>/apps/`. |
| `freemyid-1024.png` | 1024 px | Homebrew cask / macOS master (rounded tile with margin). For the `.app` use `brand/icons/platforms/freemyid.icns`. |
| `freemyid.ico` | 16, 24, 32, 48, 64, 128, 256 | Windows exe icon, installer, Start Menu shortcut. |
| `freemyid-256.png` | 256 px | winget manifest icon (IconUrl, if used) and the Microsoft Store listing. |

Naming: Flatpak requires the file to be named after the app-id (`<app-id>.svg` / `.png`) and the `.desktop` `Icon=` to match. Rename at install time once the app-id is chosen; the app-id is not decided here.
