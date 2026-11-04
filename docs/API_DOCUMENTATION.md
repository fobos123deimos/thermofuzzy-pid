# Illustrated Python API with pdoc

The [online reference](https://fobos123deimos.github.io/thermofuzzy-pid/) documents the `burnin_pid_fuzzy` package and its six implementation modules. It follows the pdoc navigation used by Fast Wave and the Intelligent Systems collection: searchable functions, signatures, source expansion, module links and rendered mathematical notation. The [versioned HTML entry](api/index.html) is also included.

## What the illustrations establish

| Figure | Source and reading |
|---|---|
| [Thermal loop](figures/thermal-loop.png) | Original signal diagram: physical state, actuator, synthetic door input, delayed/noisy measurement and stateful control |
| [FOPDT responses](figures/fopdt-responses.png) | Analytical one-unit step predictions for the four source-reported parameter records; not measured records |
| [Fuzzy scheduling](figures/fuzzy-scheduling.png) | Assumed seven-set membership geometry and proportional normalized output for sparse/dense rules, with previous outputs fixed at 0.5 |
| [Fixed loop](figures/fixed-loop-response.png) | Nominal source-parameter plant, fixed IMC gains and exact delay on 5,000 frequencies from 10⁻⁶ to 10 rad/s; not adaptive-loop stability evidence |
| [Controller comparison](../images/synthetic_controller_comparison.png) | Existing matched synthetic benchmark plot; preserved without altering its data |

New figures have editable SVG companions in `docs/figures`. Their computations use the existing package functions. No original thesis figures, private source documents or measurement records were added. pdoc covers Python; MATLAB and Simulink are linked companion implementations with their existing runtime limitations.

## Rebuild and inspect

Use Python 3.12 from the repository root:

```bash
python -m pip install -r requirements-docs.txt
python scripts/build_documentation_figures.py
python tools/build_api_docs.py
python tools/build_api_docs.py --check
python -m http.server 8000 --bind 127.0.0.1 --directory docs/api
```

Open `http://127.0.0.1:8000/`. HTTP hosting permits the search worker to operate normally; direct `file://` previews may limit browser workers. MathJax formula rendering requires an internet connection. Illustrations are local assets bundled into the site.

The build imports the package but does not run benchmarks, fetch measurements or access MATLAB. Figure regeneration is a separate, deterministic numerical command. The existing benchmark comparison image is reused, not recomputed by this command.

`--output build/api` creates an independent build. Destinations are confined to `docs/api` or beneath the checkout's `build/` directory. The builder checks every module, public function/class/method/property docstring and anchor, local image/link target, and the search index. It rejects machine-specific paths. The [build record](api/build.json) records normalized source hashes, raw source-image hashes, generated artifact hashes, render versions and coverage. `--check` detects stale documentation or modified/extra artifacts without rebuilding.

## Maintenance and publication

1. Update docstrings and, when needed, the figure script.
2. Rebuild the affected figures, rebuild the site and run `--check`.
3. Inspect formulas, search results and image readability in a browser.
4. Commit the source, source figures and generated `docs/api` together.

The [API workflow](../.github/workflows/api-docs.yml) verifies committed documentation, rebuilds separately, checks that output and publishes successful `main` builds through GitHub Pages. Repository Settings → Pages must select GitHub Actions. Publication is complete only after the deployment job succeeds; the guide alone does not assert a live deployment.

The render dependencies are pinned in [requirements-docs.txt](../requirements-docs.txt). Scientific dependencies retain the package's declared ranges. Generated HTML is preserved verbatim and marked as generated for reviews. Documentation tests do not expand the original experimental claims or validate physical hardware.

The [local validation record](api-validation.json) records 18 passing tests, an executed getting-started example and unchanged executable syntax trees across all seven Python source files. All five figures were visually inspected. Browser rendering and the public deployment must be confirmed separately from these local checks.

References: [pdoc](https://pdoc.dev/docs/pdoc.html), [pdoc rendering configuration](https://pdoc.dev/docs/pdoc/render.html), [GitHub Pages custom workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).
