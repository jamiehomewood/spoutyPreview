# spoutyPreview

See a Spout feed the way the Igloo room shows it. You stand in the middle of a virtual copy of the room
and turn your head to look around. The room stays still, and faint lines show where the walls, floor and ceiling meet.

The feed is treated as a 2:1 equirectangular 360 image (e.g. 4096 × 2048), with the image centre on the front wall.
Four walls and the floor are projected; the ceiling is left dark.

## Build the exe (Windows)

Double-click **BUILD_EXE.bat**. It makes a single portable `spoutyPreview.exe` in this folder.

The build uses Python 3.13 (or 3.12) in a private `.build-venv` folder, because SpoutGL has no build for Python 3.14 yet.
If 3.13 isn't installed, it installs it with winget alongside your current Python. You only need Python for the build;
the exe runs on any Windows PC.

To run it without building: `pip install pygame-ce PyOpenGL SpoutGL`, then `python spoutyPreview.py`
(`--image pano.jpg` shows a still 360 image instead of Spout).

## Settings

`spoutyPreview.ini` sits next to the exe. It holds the room size (default 6.40 × 5.71 × 2.244 m), eye height,
projection-centre height and feed options. Edit it and press **L** to reload, or change things in the app and press **Ctrl+S**.

## Controls

| | |
|---|---|
| Drag / arrow keys | Turn your head |
| Scroll | Zoom |
| R | Face front again |
| 1 2 3 4 / 5 | Face front / right / back / left, or look at the floor |
| E | Room edges: faint, off, brighter |
| W/S, D/A, T/G | Room width, depth, height (Shift = 1 cm steps) |
| [ ] | Projection-centre height |
| , . | Rotate the feed to line up the front wall |
| F / M | Flip the feed vertically / mirror it |
| Ctrl+S / L | Save / reload settings |
| H | Hide the help |
| Esc | Quit |

See also [spoutyModel](https://github.com/jamiehomewood/spoutyModel), which views 3D models and full scenes in the same room.
