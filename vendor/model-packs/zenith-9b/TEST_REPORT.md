# Qwythos GGUF v2 release verification

Release verification was performed on 2026-06-22 with llama.cpp `d0f9d2e5ac5d4f51763755958b8f353fed01aaa2` and an NVIDIA RTX 5090.

## Artifact manifest

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `Qwythos-9B-Claude-Mythos-5-1M-BF16.gguf` | 17,920,697,344 | `c49e2e419c0fc9f7cca0a7e0699fa3075fa1ec2913bda6f6841194b19cf4ce29` |
| `Qwythos-9B-Claude-Mythos-5-1M-Q4_K_M.gguf` | 5,629,109,248 | `0de41ff56ab4eff26764437b276f0bd5d20f44232add34e14c4f593fa1aeb08f` |
| `Qwythos-9B-Claude-Mythos-5-1M-Q5_K_M.gguf` | 6,467,970,048 | `51dee6e6ddaeb08a06bee258ac5c58f4186f55d156d6403c2db67cf2f3226280` |
| `Qwythos-9B-Claude-Mythos-5-1M-Q6_K.gguf` | 7,359,259,648 | `05f2420a669a83ae239d1328c6e83d9fc19e8a4b8dab5d0673cab28cc161dfc5` |
| `Qwythos-9B-Claude-Mythos-5-1M-Q8_0.gguf` | 9,527,501,824 | `ecf51ef3904694e04a1967a06fe7539619c34e6e81a721fc5f5415827081d8f6` |
| `Qwythos-9B-Claude-Mythos-5-1M-MTP-BF16.gguf` | 18,407,321,536 | `c704996e63c3e31a1e7040278b1204aabf8a6dad0b07f3c8da7b429d2ed30b31` |
| `Qwythos-9B-Claude-Mythos-5-1M-MTP-Q4_K_M.gguf` | 5,887,668,160 | `24ee22e0f5d9f0d3d615809607f365c728d9b0c3f3fb6eb19d8bd83a1c2933d8` |
| `Qwythos-9B-Claude-Mythos-5-1M-MTP-Q5_K_M.gguf` | 6,726,528,960 | `c4e3c47b17a93cc1566abcee4a0c9a4413b172a6f8be7f2a8824495907e9e893` |
| `Qwythos-9B-Claude-Mythos-5-1M-MTP-Q6_K.gguf` | 7,617,818,560 | `eae2adb4b451f673218fba96ebdc024fb95c4026ef35a56837dc9af47f99ca39` |
| `Qwythos-9B-Claude-Mythos-5-1M-MTP-Q8_0.gguf` | 9,786,060,736 | `34eada291b4f4d1b8592f53d1739c7a2e029011b5bc2624b979b0a544562a5e9` |
| `mmproj-Qwythos-9B-Claude-Mythos-5-1M-F16.gguf` | 918,165,472 | `f977efc337a2ac2ba183eea0c73e25b75fc240d56c05ed4d9b56ab451f64c82c` |

`shasum -a 256 -c SHA256SUMS` passed for all 11 GGUF artifacts after conversion and testing.

## Structural checks

All ten text GGUFs passed these shared assertions:

- GGUF v3 and `qwen35` architecture;
- 1,048,576-token declared context;
- Qwen3.6-derived chat template markers present;
- fixed Qwythos/Empero AI identity instruction present.

The five normal v2 replacement files additionally verified as 32-block trunk-only GGUFs with no `nextn_predict_layers` key and no MTP tensors.

The five `-MTP-` v2 variants additionally verified as 33-block GGUFs with `qwen35.nextn_predict_layers = 1`, all 15 restored MTP tensors present, and MTP matrices retained at Q8_0 in every quantized variant.

The MTP tensors come from pinned Qwen3.5-9B base commit `c202236235762e1c871ad0ccb60c8ee5ba337b9a`. The source fine-tune declares one MTP layer but does not publish its MTP tensors. Only the draft head is restored; the Qwythos trunk and output layers remain unchanged.

## Live tests

| Variant / mode | Identity | Generation | Tools | Other |
|---|---:|---:|---:|---|
| BF16 MTP | Pass | Pass | — | — |
| Q4_K_M MTP | Pass | Pass | Pass | Tool result round trip passed |
| Q5_K_M MTP | Pass | Pass | — | — |
| Q6_K MTP | Pass | Pass | — | — |
| Q8_0 MTP | Pass | Pass | Pass | Tool result round trip passed; no malformed output |
| Q4_K_M MTP + draft speculation | Pass | Pass | Pass | 76/150 draft tokens accepted (50.7%) |
| Q4_K_M MTP + 1M context | Pass | Pass | — | Server loaded `n_ctx = 1048576` |
| Q4_K_M MTP + F16 mmproj | Pass | Pass | — | Correctly identified a generated red-square image |

The normal v2 replacement files were rebuilt from the same fixed tokenizer/template source with `--no-mtp` and structurally verified after quantization. The 1M-context check verifies full context allocation and successful generation at that setting; it is not a million-token retrieval benchmark.

Machine-readable responses are in `reports/`; relevant llama.cpp logs are in `logs/`.
