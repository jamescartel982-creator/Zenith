# Check the release files

Zenith 0.8 inventories every Git-tracked source release file except the manifest itself in `release-manifest.json`: runtime code, web assets, installers, workflows, tests, documentation, starter resources, catalog snapshots, pinned model-pack inventories, all 43 vendored support/source files, and the preserved starter archive.

Get the complete source ZIP through GitHub's **Code → Download ZIP** or the README link. GitHub generates it from the committed tree. Local data, secrets, downloads, and trained artifacts are not part of that tree. The 89 model-pack weight artifacts are inventoried and downloaded/verified separately with `zenith packs`, not bundled.

## Source checkout or ZIP

After upgrading, run from the extracted root:

```text
zenith verify --source .
zenith verify --source . --json
```

Use `./run.sh verify --source .` on Linux, or `powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1 verify --source .` on Windows. Git is not needed for verification. Missing/modified files, invalid entries, unsafe paths, omitted required entries, or a different running release version cause a nonzero exit code.

UTF-8 source text uses CRLF-to-LF normalization so Windows wrappers and GitHub ZIPs remain compatible. Binary checks use exact bytes. Intentional edits correctly change the result. Untracked files are outside the inventory; this does not recursively scan personal data.

Maintainers: stage all reviewed release files, run `python -m scripts.build_release_manifest`, then commit the manifest. Regenerate after any further tracked-file edit. The builder lists tracked files rather than ignored/private directories and excludes the impossible self-hash. Do not regenerate merely to suppress an unexplained mismatch.

## Installed wheel

```text
zenith verify
zenith verify --json
```

This checks installed distribution records, including packaged code/resources and entry points. Generated/unhashed metadata is counted separately. It detects source shadowing and code/version mismatches. Editable development installs do not inventory source files, so they direct you to `--source PATH` instead of reporting a misleading complete pass. Normal installers and Docker use regular wheels.

The wheel contains runtime packages/data. The complete source archive additionally includes repository docs, tests, installers, and vendored sources. Docker contains the installed runtime plus selected documentation, sample configuration, and support sources; verify its wheel with `docker compose exec zenith zenith verify`.

These checks establish **consistency**, not publisher authenticity or a digital signature: someone who changes both files and inventory can replace both. Obtain the intended repository/commit and retain third-party notices. File checks do not certify answer quality or inspect external model weights.
