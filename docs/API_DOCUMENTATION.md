# Illustrated Python API with pdoc

The [online reference](https://fobos123deimos.github.io/thermofuzzy-pid/) documents the `burnin_pid_fuzzy` package and its six implementation modules. It follows the pdoc navigation used by Fast Wave and the Intelligent Systems collection: searchable functions, signatures, source expansion, module links and rendered mathematical notation. The [versioned HTML entry](api/index.html) is also included.

## What the illustrations establish

The [detailed thermal-control atlas](DIAGRAMS.md) adds six original TikZ plates: an illustrative chamber cutaway, source-model identification, PID/IMC and anti-windup, the three exact sparse fuzzy matrices, robustness, and optimization with a held-out evaluation boundary. Each has an editable source, vector PDF and 2,800-pixel PNG. The complete [atlas PDF](figures/tikz/thermal-control-atlas.pdf) is also bundled in the pdoc site at [assets/thermal-control-atlas.pdf](https://fobos123deimos.github.io/thermofuzzy-pid/assets/thermal-control-atlas.pdf); the navigation and relevant module pages link it locally.

The new drawings preserve the distinction between thesis parameters, reconstruction assumptions and synthetic experiments. Sensor placement is illustrative; the known-delay ARX example reports fitted residuals, and independent identification validation is explicitly a recommended extension. The optimization notebook has its own implemented train/test split.

The [atlas review record](tikz-atlas-review.json) records six visually reviewed plates, 147 checked sparse consequents and preservation of the existing numerical materials. The expanded pdoc build validates eight HTML pages, 2,827 local links, eleven PNG illustrations and the vector atlas; the [build manifest](api/build.json) hashes the served PDF alongside every image.

| Figure | Source and reading |
|---|---|
| [Thermal loop](figures/thermal-loop.png) | Original signal diagram: physical state, actuator, synthetic door input, delayed/noisy measurement and stateful control |
| [FOPDT responses](figures/fopdt-responses.png) | Analytical one-unit step predictions for the four source-reported parameter records; not measured records |
| [Fuzzy scheduling](figures/fuzzy-scheduling.png) | Assumed seven-set membership geometry and proportional normalized output for sparse/dense rules, with previous outputs fixed at 0.5 |
| [Fixed loop](figures/fixed-loop-response.png) | Nominal source-parameter plant, fixed IMC gains and exact delay on 5,000 frequencies from 10⁻⁶ to 10 rad/s; not adaptive-loop stability evidence |
| [Controller comparison](../images/synthetic_controller_comparison.png) | Existing matched synthetic benchmark plot; preserved without altering its data |

The earlier four explanatory/computed figures have editable SVG companions in `docs/figures`; their computations use the existing package functions. They and the benchmark comparison remain unchanged. No original thesis figures, private source documents or measurement records were added. pdoc covers Python; MATLAB and Simulink are linked companion implementations with their existing runtime limitations.

## Rebuild and inspect

Use Python 3.12 from the repository root:

```bash
python -m pip install -r requirements-docs.txt
python scripts/build_documentation_figures.py
python tools/build_api_docs.py
python tools/build_api_docs.py --check
python tools/build_tikz_atlas.py --check
python -m http.server 8000 --bind 127.0.0.1 --directory docs/api
```

Open `http://127.0.0.1:8000/`. HTTP hosting permits the search worker to operate normally; direct `file://` previews may limit browser workers. MathJax formula rendering requires an internet connection. Illustrations are local assets bundled into the site.

The build imports the package but does not run benchmarks, fetch measurements or access MATLAB. Figure regeneration is a separate, deterministic numerical command. The existing benchmark comparison image is reused, not recomputed by this command.

To edit the new diagrams, follow the [atlas build instructions](DIAGRAMS.md#reproduce-and-interpret). The TikZ build uses Tectonic, Poppler and pypdf; `--check` requires only the standard library and verifies the six source sets, exact fuzzy table export, PDF/PNG hashes and minimum image resolution. CI checks the committed atlas before rebuilding pdoc. All five notebooks include topic-specific image context without changing their code cells or outputs.

`--output build/api` creates an independent build. Destinations are confined to `docs/api` or beneath the checkout's `build/` directory. The builder checks every module, public function/class/method/property docstring and anchor, local image/link target, and the search index. It rejects machine-specific paths. The [build record](api/build.json) records normalized source hashes, raw source-image hashes, generated artifact hashes, render versions and coverage. `--check` detects stale documentation or modified/extra artifacts without rebuilding.

## Maintenance and publication

1. Update docstrings and, when needed, the figure script.
2. Rebuild the affected figures, rebuild the site and run `--check`.
3. Inspect formulas, search results and image readability in a browser.
4. Commit the source, source figures and generated `docs/api` together.

The [API workflow](../.github/workflows/api-docs.yml) verifies committed documentation, rebuilds separately, checks that output and publishes successful `main` builds through GitHub Pages. Repository Settings → Pages selects GitHub Actions. Future publication is complete only after the deployment job succeeds.

The first public deployment was verified on **4 November 2026** for source `2711d22c870cbfefb5f9e859db95d3fa57ca06b0`. [API run 41914672749](https://github.com/fobos123deimos/thermofuzzy-pid/actions/runs/41914672749), attempt 2, passed its build and deployment checks after Pages was enabled: seven modules, 28 public definitions, eight HTML pages, 2,783 local links and five illustrations. The [Python test run](https://github.com/fobos123deimos/thermofuzzy-pid/actions/runs/41914672854) passed all 18 tests, synthetic-data generation and the benchmark script on both Python 3.10 and 3.12.

The render dependencies are pinned in [requirements-docs.txt](../requirements-docs.txt). Scientific dependencies retain the package's declared ranges. Generated HTML is preserved verbatim and marked as generated for reviews. Documentation tests do not expand the original experimental claims or validate physical hardware.

The [validation record](api-validation.json) identifies publication jobs and preserves the local evidence: 18 passing tests, an executed getting-started example and unchanged executable syntax trees across all seven Python source files. All five figures were visually inspected. The public homepage displayed the thermal-loop image, rendered FOPDT equation, introductory example and comparison figure; searching for `FuzzyRuleBase` returned twelve results. This browser check samples presentation and search, while structural checks cover all generated pages.

References: [pdoc](https://pdoc.dev/docs/pdoc.html), [pdoc rendering configuration](https://pdoc.dev/docs/pdoc/render.html), [GitHub Pages custom workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).
