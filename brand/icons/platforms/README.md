# Platform app icons

Source: the Free My ID mark (navy tile, white star, red flag bar). Built by `brand/src/build_platform_art.py`.

| Path | Use |
|---|---|
| `freemyid.icns` | macOS `.app`: `Contents/Resources/freemyid.icns`, and `CFBundleIconFile` = `freemyid` in Info.plist. Built with Pillow (no iconutil on Linux); has 16-512 plus @2x. |
| `freemyid.iconset/` | Standard iconset PNGs (16 to 512@2x). On a Mac, `iconutil -c icns freemyid.iconset` rebuilds a native .icns if preferred (e.g. for notarized builds). |
| `freemyid-macos.svg`, `freemyid-macos-1024.png` | 1024 master with the macOS margin (about 10%) and rounded tile. |
| `hicolor/<N>x<N>/apps/freemyid.png` (16, 22, 24, 32, 48, 64, 128, 256, 512) | Linux icon theme. Install to `/usr/share/icons/hicolor/` or `~/.local/share/icons/hicolor/` (AppImage, .deb, Flatpak, AUR). |
| `hicolor/scalable/apps/freemyid.svg` | Linux scalable icon (small margin, full-bleed tile). |

`.desktop` file: `Icon=freemyid` (theme name, no extension). Flatpak app-id icons must be renamed to `<app-id>.png/.svg`.
The icon is the same in light and dark mode (a solid tile that holds on both).
Alt text if shown on a page: "Free My ID app icon".
