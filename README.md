# Phaseline

A ten-lane rhythm game for desktop and Android, built in Godot 4.7. Five electronic arrangements of classical works each have Easy, Medium, Hard, and Expert charts. All game assets are bundled for offline play.

## Play

**Android 7.0 and newer.** Download [Phaseline-Android.apk](https://github.com/maccam912/phaseline/releases/latest/download/Phaseline-Android.apk) on your device and open it. If prompted, allow your browser or file manager to install the app. Play in landscape. Tap the numbered pads as notes reach the hit line, use multiple fingers for chords, and keep a finger down through the tail of a hold. Tap Pause or use Android Back to pause a song.

**Desktop.** Install Phaseline from the [game launcher](https://github.com/maccam912/launcher), or download and extract the ZIP for your platform from the [latest release](https://github.com/maccam912/phaseline/releases/latest). macOS builds support Apple Silicon and Intel. Windows and Linux builds target x86-64.

To run from source, install Git LFS and Godot 4.7.2, then clone the project and import the assets.

```sh
git lfs install
git clone https://github.com/maccam912/phaseline.git
cd phaseline
git lfs pull
godot --headless --editor --import --path .
godot --path .
```

On a keyboard, use **↑ / ↓** to browse, **Space** to preview, **← / →** to change difficulty, and **Enter** to start. Put your hands on **A S D F G · H J K L ;** and tap each key as its note crosses the hit line. Your index fingers cover F/G and H/J. Hold long notes through their tails. **Esc** pauses. The game saves your best score separately for each song and difficulty.

Easy plays one key at a time. Medium and Hard allow two simultaneous keys, with denser rhythms on Hard. Expert adds stacked chords for up to eight fingers. Sustained notes count toward each limit.

Settings include independent music and hit volumes, reduced motion, and timing calibration. Desktop players can also rebind keys and toggle fullscreen. For calibration, use your usual speakers or headphones and tap along with eight clicks using the on-screen button or Space.

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

GitHub Actions builds all four platforms on each push to `main`. You can also start a release from the Actions tab on `main`. Versions use the major and minor from `project.godot` and the release workflow’s run number for the patch, for example `v1.1.3`. Android uses the same run number as its update code. Re-running the same workflow run keeps its number. The release includes three desktop ZIPs and a SHA-256 checksum file. The signed Android APK is also listed in the checksums once published.

For Android releases, the maintainer can sign on their own machine using the original Phaseline release keystore (alias `phaseline`). Set `ANDROID_HOME` to an Android SDK with Build Tools 35.0.1 installed, authenticate `gh` with release access, and run the following command with the published tag and private keystore path. The helper downloads the matching build, prompts for the keystore password, verifies the signature, then uploads the APK and updated checksums. The signing key stays on the machine.

```sh
python3 .github/scripts/publish_android.py v1.1.3 --keystore /path/to/phaseline.p12
```

For unattended signing, the workflow also supports the encrypted repository secrets `ANDROID_KEYSTORE_BASE64` and `ANDROID_KEYSTORE_PASSWORD`. When both are configured, it verifies and publishes the signed APK together with the desktop builds.

For local exports, install the Godot export templates matching your editor version and run the desired command from the project root. The bundled recordings let you build on any platform without installing Logic Pro.

```sh
mkdir -p build/macos build/windows build/linux build/android
godot --headless --export-release macOS build/macos/Phaseline.zip
godot --headless --export-release Windows build/windows/Phaseline.exe
godot --headless --export-release Linux build/linux/Phaseline.x86_64
godot --headless --export-debug Android build/android/Phaseline-Android.apk
```
