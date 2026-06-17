# GenomeLens Patchset

Initial construction vendors the upstream source tree without intentional algorithm changes. GenomeLens engine wrapper code lives in `src/jcvi_genomelens/`.

## Windows compatibility patches

- `src/jcvi/_version.py`: fixed vendored source version metadata to `1.6.5`, replacing the upstream build-time generated file.
- `src/jcvi/apps/base.py`: guard `signal.SIGPIPE` setup because Windows Python does not expose `SIGPIPE`.
- `src/jcvi/apps/base.py`: allow `which()` to resolve `.exe` suffixes on Windows.
- `src/jcvi/apps/base.py`: use the platform default shell instead of `/bin/bash` for `sh()` and `Popen()` on Windows.
- `src/jcvi/graphics/tree.py`: fall back from `ete4` to `ete3` for Windows runtime compatibility.
