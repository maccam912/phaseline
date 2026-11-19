# Soundtrack credits

Phaseline’s stereo mixes are original electronic arrangements of public-domain compositions. The recorded piano, ensemble instruments and drum kits come from the licensed Logic Pro sound library installed on the production Mac. They play newly sequenced parts alongside original synthesizer patches. The completed mixes play offline on desktop and Android.

| Game track | Source composition | Arrangement |
| --- | --- | --- |
| Midnight Current | Johann Sebastian Bach, *Prelude in C major*, BWV 846, from *The Well-Tempered Clavier*, Book I (1722 or earlier). [Netherlands Bach Society](https://www.bachvereniging.nl/en/bwv/bwv-846) | Steinway arpeggios and a wide analog lead over Neon drums |
| Glass Circuit | Ludwig van Beethoven, *Für Elise*, WoO 59 (1810, first published 1867). [Beethoven-Haus manuscript catalogue](https://katalog.beethoven.de/cgi-bin/biblio/hans_en.pl?reccheck=2163&t_show=x&wert=BH+116&wertreg=SIG&x=u) · [Beethoven-Haus work catalogue and first edition](https://www.beethoven.de/de/work/view/ag9iZWV0aG92ZW4tdml1cjNyEQsSBHdvcmsYgICArO2tuwkM/Bagatelle%2Bfor%2Bpiano%2B%26%23040%3BA%2Bminor%26%23041%3B%2BWoO%2B59) | Steinway, Mark II electric piano and organ over a swung Beat Machine two-step |
| Velvet Orbit | Erik Satie, *Gymnopédie No. 1* (1888). [Bibliothèque nationale de France](https://catalogue.bnf.fr/ark:/12148/cb13918639z) | A Mark II electric-piano waltz with solo flute, strings and Crate Digger percussion |
| Breakpoint | Edvard Grieg, *In the Hall of the Mountain King*, from *Peer Gynt* (incidental score completed in 1875). [Boston Symphony Orchestra](https://www.bso.org/works/grieg-peer-gynt-bill-barclay-adaptation) | Marching horns, clarinet, strings and Pile Driver breakbeats |
| Afterimage | Wolfgang Amadeus Mozart, *Alla turca*, third movement of the Piano Sonata in A major, K. 331 (autograph dated 1783). [Stiftung Mozarteum Salzburg](https://kv.mozarteum.at/work/alla-turca-4103) | A flute opening, Mozart’s A-major octave march, trumpet section and Big Room drums |
| Maple After Hours | Scott Joplin, *Maple Leaf Rag* (1899). [Johns Hopkins, original sheet music](https://levysheetmusic.mse.jhu.edu/collection/171/088) | Plucked upright bass walks beneath the Steinway and Mark II electric piano. Solo clarinet trades strains with the piano over Silverlake drums. |
| Cinder Step | Georges Bizet, Habanera from *Carmen* (1875). [Choudens vocal score](https://s9.imslp.org/files/imglnks/usimg/8/8f/IMSLP851704-PMLP15769-Bizet%2C_Carmen%2C_Habanera.pdf) | Muted electric bass plays the dotted dance rhythm under solo clarinet and Trap Door drums. Bowed strings take the major-key refrain before an electric piano break. |
| First Light | Antonio Vivaldi, *Spring*, RV 269, first movement (published 1725). [Original violin part, reproduced by the Library of Congress, p. 7](https://www.loc.gov/static/programs/national-recording-preservation-board/documents/The-Four-Seasons_Furuya.pdf#page=7) | Bowed strings carry the opening refrain over an offbeat synth bass and After Party drums. Solo flute and tuned metal mallets answer in the quieter middle section. |

## Use and redistribution

The historical compositions are in the public domain in the United States. Copyright in a composition and copyright in a particular sound recording are separate. These references describe the distinction and how publication dates affect the U.S. term. [U.S. Copyright Office on musical works and recordings](https://www.copyright.gov/register/pa-sr.html) · [Circular 22, historical copyright terms](https://www.copyright.gov/circs/circ22.pdf)

The project makes its original arrangements and note charts available under **CC0 1.0 Universal** to the extent it holds rights in them. [CC0 summary](https://creativecommons.org/publicdomain/zero/1.0/) · [CC0 legal code](https://creativecommons.org/publicdomain/zero/1.0/legalcode)

The current MP3 masters incorporate Apple-licensed sound content. Apple permits original soundtracks made with its content to be distributed royalty-free, including commercially. Apple and its licensors retain their rights in the underlying samples and restrict standalone redistribution and repackaging of that content. The project’s CC0 dedication covers its arrangement and chart contributions. Use the finished mixes as this game’s soundtrack under the applicable terms. [Apple’s Logic Pro commercial-use guidance](https://support.apple.com/en-us/101908)

The earlier oscillator-only edition, including its recordings and original four-lane charts, retains its original CC0 dedication. The local build archive `build/Phaseline-Original-CC0-Soundtrack.zip` contains that edition with its catalogue and credits.

During arrangement, the project also consulted these public-domain score transcriptions. [Mozart’s Alla turca](https://www.mutopiaproject.org/ftp/MozartWA/KV331/KV331_3_RondoAllaTurca/KV331_3_RondoAllaTurca-a4.pdf) · [Grieg’s In the Hall of the Mountain King](https://www.mutopiaproject.org/ftp/GriegE/O46/Dans_l_antre_du_roi_de_la_montagne/Dans_l_antre_du_roi_de_la_montagne-a4.pdf) · [Satie’s Gymnopédie No. 1](https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=37)

## Rebuilding the audio

From the project root, run `python3 tools/music/render.py` with NumPy, SciPy, FFmpeg with libmp3lame, and the licensed Logic Pro sound content listed below installed. The renderer sequences the local instrument recordings directly and writes finished stereo MP3s and a chart catalogue. Normal game playback requires only the files already in the game.

- The EXS Steinway Grand Piano 2 instrument and its consolidated D-274 recording.
- Alchemy’s EPiano Mrk II, 60s Transistor Organ, MMBass Mute and Bell Attack Pad.
- The factory Upright Jazz Bass, String Ensemble, Flute Solo, Clarinet Solo, French Horns and Trumpets from the shared GarageBand instrument library.
- The Neon, Beat Machine, Crate Digger, Pile Driver, Big Room, Silverlake, Trap Door and After Party kits under Ultrabeat Samples / Drum Machine Designer.

The default factory sound locations are `/Library/Application Support/Logic` and `/Library/Application Support/GarageBand`. Set `PHASELINE_LOGIC_LIBRARY` or `PHASELINE_GARAGEBAND_LIBRARY` when those folders have been relocated. To rebuild only the charts use `python3 tools/music/render.py --charts-only`; this operation has no dependency on the factory sounds.
