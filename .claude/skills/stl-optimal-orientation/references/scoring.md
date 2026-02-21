# Orientation Scoring Weights

The composite score uses these weights:

| Factor | Weight | Goal |
|--------|--------|------|
| Bed contact area | 0.35 | Maximize flat surface touching bed |
| Overhang area | 0.30 | Minimize unsupported downward faces |
| CoG height | 0.15 | Lower center of gravity = more stable |
| Cross-section at centroid | 0.20 | Larger cross-section = better bed support |

## Tuning

For **functional parts** (strength matters): increase overhang weight to 0.40, reduce cross-section to 0.10.

For **visual parts** (surface quality matters): increase bed contact to 0.45 (fewer support marks on visible faces).

For **tall thin parts**: increase CoG weight to 0.25 to prevent toppling.
