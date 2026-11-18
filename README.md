# Phaseline

A ten-lane desktop rhythm game built in Godot 4.7. Five electronic arrangements of classical works each have Easy, Medium, Hard, and Expert charts. All game assets are bundled for offline play.

## Play

Download the ZIP for your desktop from the [latest release](https://github.com/maccam912/phaseline/releases/latest). Extract it and launch Phaseline. macOS builds support Apple Silicon and Intel. Windows and Linux builds target x86-64.

To run from source, install Git LFS and Godot 4.7.2, then clone the project and import the assets.

```sh
git lfs install
git clone https://github.com/maccam912/phaseline.git
cd phaseline
git lfs pull
godot --headless --editor --import --path .
godot --path .
```

Use **↑ / ↓** to browse, **Space** to preview, **← / →** to change difficulty, and **Enter** to start. Put your hands on **A S D F G · H J K L ;** and tap each key as its note crosses the hit line. Your index fingers cover F/G and H/J. Hold long notes through their tails. **Esc** pauses. The game saves your best score separately for each song and difficulty.

Easy plays one key at a time. Medium and Hard allow two simultaneous keys, with denser rhythms on Hard. Expert adds stacked chords for up to eight fingers. Sustained notes count toward each limit.

Settings include independent music and hit volumes, key rebinding, fullscreen, reduced motion, and timing calibration. For calibration, use your usual speakers or headphones and tap Space along with eight clicks.

## Soundtrack

| Track | Source | Arrangement |
| --- | --- | --- |
| Midnight Current | Bach’s Prelude in C major, BWV 846 | Synthwave · 116 BPM |
| Glass Circuit | Beethoven’s Für Elise | UK garage · 132 BPM |
| Velvet Orbit | Satie’s Gymnopédie No. 1 | Downtempo waltz · 90 BPM |
| Breakpoint | Grieg’s In the Hall of the Mountain King | Drum and bass · 156 BPM |
| Afterimage | Mozart’s Alla turca | Electro house · 128 BPM |

The historical compositions are in the U.S. public domain. The finished game mixes combine original synthesizers with licensed Logic Pro instruments and drum kits. The arrangements and charts are available under CC0. See the [soundtrack credits](music/CREDITS.md) for composition sources, recording terms, and offline rendering instructions. The [cover-art notes](assets/covers/ARTWORK.md) document the illustrations. Font and Godot notices are in `assets/fonts` and `assets/licenses`.

## Export

GitHub Actions builds and publishes a release on each push to `main`. You can also start a release from the Actions tab on `main`. Versions use the major and minor from `project.godot` and the release workflow’s run number for the patch, for example `v1.1.1`. Re-running the same workflow run keeps its number. Each release includes three platform ZIPs and a SHA-256 checksum file.

For local exports, install the Godot export templates matching your editor version and run the desired command from the project root. The bundled recordings let you build on any platform without installing Logic Pro.

```sh
mkdir -p build/macos build/windows build/linux
godot --headless --export-release macOS build/macos/Phaseline.zip
godot --headless --export-release Windows build/windows/Phaseline.exe
godot --headless --export-release Linux build/linux/Phaseline.x86_64
```
