# Fleiss Kappa

Fleiss' Kappa is an inter-rater agreement statistic used when more than two raters classify the same items into nominal categories. In Istara's corrected research-validity contract, the items are stable qualitative evidence units and the raters are independent human/model coders using the same governed codebook.

Istara must not describe whole-response keyword buckets as formal Fleiss' Kappa qualitative reliability. Those can be operational consensus signals, but formal reliability requires coded evidence-unit matrices, route/model identity, and the default `kappa >= 0.60` promotion gate unless project policy explicitly overrides it.

The item-by-rater matrix must be complete. A missing or empty unmarked response is not a `none` category and blocks metric computation; an intentional abstention must be explicit and is preserved separately. When every rating occupies a single category, expected agreement is 1.0 and Fleiss' Kappa is undefined, so Istara requires reconciliation rather than treating perfect raw agreement as beyond-chance reliability.

References: Fleiss (1971), Cohen (1960), O'Connor & Joffe (2020), MacQueen et al. (1998). See `docs/architecture/research-validity-contract.md`.
