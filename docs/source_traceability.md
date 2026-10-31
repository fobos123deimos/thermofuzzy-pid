# Source traceability and decisions

For the additional theory-based Drive/Dropbox review, consult [Theoretical foundations](theoretical_foundations.md) and [Source audit](source_audit.md). No PDF or private Drive/Dropbox material is included in the public repository.

**Private source reviewed:** Matheus Gomes Cordeiro, *Projeto de um Controlador PID-Fuzzy para a Câmara de Burn-in* (UFC, 2021). The user's source PDF is not in this repository.

## Mapping

| Source location (printed page) | What was available | Code and status |
|---|---|---|
| p. 17, Eq. 2.1 | Combined process/sensor FOPDT transfer function | `models.py`: source-derived mathematical class, assigning the delay to sensor path is an assumption |
| pp. 18–21 | P/I/D equations, ISA form, filtered derivative | `controllers.py` and MATLAB standalone, converted to **independent** gain notation |
| pp. 23–25 | Mamdani min/max, M-o-M | `fuzzy.py` and `fuzzy_mom_gains.m` |
| p. 29, Eq. 2.13 | Signed error and first difference | Uses signed delta error, and nonnegative `abs(error)` to fit stated membership domain |
| p. 29, Eq. 2.14 | Affine gain mapping | Fuzzy PID normalized gain conversion |
| pp. 30–32 | TH37/TH34 and two averaging models | `PLANTS_FROM_THESIS`, `thesis_parameters.m` |
| p. 33, Table 2 | IMC controller | `imc_pid_gains` in Python and MATLAB |
| p. 35, Fig. 14 | Seven input terms, five output terms | Equally spaced MF coordinates **assumed**, not recovered exactly |
| p. 36, Fig. 15 | 7×7 rule table (2 omitted columns) | Sparse rule matrix manually transcribed; no automatic OCR |
| p. 36, Table 4 | Min/max gains | `[.35,.0008,0]` and `[.90,.045,2]` |
| p. 37 | Target 65 °C; disturbance t=200 and t=300 in 10 s axis | Events at 2000 and 3000 **seconds** |
| pp. 40–41 | Historical ~22%/3% comparative observation | **Reported-only**; synthetic results have independent provenance |
| p. 42 | Future work: second derivative, missing rules, genetic/evolutionary and neurofuzzy comparison | Documented research directions and notebook 04 extension |

## Resolved inconsistencies and open unknowns

1. **Units of dead time:** the continuous parameter `theta` is seconds. The discrete model cannot simply use `z^-theta` without defining a sample period. We explicitly use a 1-second timestep and linear interpolation for the fractional sensor delay.
2. **Input error domain:** the paper gives `e=r-y` while graphing its `e` membership functions on `[0,40]` and describing absolute error. We take `|e|` as the nonnegative FIS input and use signed `Delta e` for the second input.
3. **MF vertex coordinates:** the figure shows shapes but does not enumerate vertex coordinates; evenly spaced peak locations are a documented *new parameterization*.
4. **Untuned gain conventions:** `Ki` and `Kd` can denote the independent gains or normalized $1/T_i$ and $T_d$, depending on PID convention. Our PID uses `Ki=Kp/Ti`, `Kd=Kp Td` consistently.
5. **Sparse cells:** the thesis describes unspecified gain values as unchanged. We retain the previous gain for isolated omissions or missing entire columns. First-time gain normalization `0.5` is an implementation assumption.
6. **Separate plant and sensor dynamics:** the measured combined `GH(s)` does not uniquely identify which component generates `theta`. A physical sensor-delay allocation is used for simulation only.
7. **Actuator units and thermal capacity:** no calibration of the simulated command `0..10` to actual gas-valve drive or watts appears in this implementation. Door heat-loss magnitudes are illustrative.
8. **Original ARX coefficients:** the source lists discrete ARX estimates, but not sample interval and raw input data sufficient to reproduce identification or the plotted MATLAB validation metrics. We use direct least squares on synthetic FOPDT data, explicitly a separate experiment.
9. **Reported percent improvements:** not independently verified: the reported original experimental curves and Simulink projects were not available. We cannot claim that any run reproduces the original published percentages.
10. **Simulink validation:** programmatic sources are present; a licensed MATLAB run is required to produce and compile the `.slx` model.

## Advisor identity

Professor Dr. **José Tarcísio Costa Filho**, named as undergraduate thesis supervisor on the title/approval page, is listed by the UFC DETI official staff directory with a direct Lattes link:

- [UFC faculty directory](https://deti.ufc.br/pt/corpo-docente/professores-efetivos/)
- [Lattes (UFC-listed official link)](https://buscatextual.cnpq.br/buscatextual/visualizacv.do?id=K4785436Z5&metodo=apresentar)

The Lattes system may require a visual security code. This repository does not mirror private curriculum data.


## Additional archive-derived foundations (theory only)

| Privately reviewed material | Verified topic | Current implementation |
|---|---|---|
| Google Drive: *Relatório Parcial 1 — Controle de Temperatura Média em Câmara de Burn-in* | Experimental identification, ARX, first-order models, IMC | `identification.py`: new transparent ARX(1,1,delay) teaching formulation; not the original source data |
| Google Drive: *Relatório Parcial 2 — Implementação de Algoritmos PI e PID em CLP* | Explicit back-calculation anti-windup and GM/PM/$M_s$ concepts | `controllers.py`: optional back-calculation and `robustness.py`: fixed linear loop analysis |
| Google Drive: *Modelos de Processos e de Perturbação* and two identification slide sets | Regressor design and least-squares parameter fitting | `identification.py`, notebook 05 |
| Google Drive: editable *Tabela Verdade* | Linguistic-rule evidence and missing columns | Original sparse table retained, ambiguous repeated gain-label highlighted in theory docs |
| Google Drive: De Luca (2004), UFSC master's dissertation | Thermal stress, chamber spatial profiling, measurement uncertainty | New theoretical warning: mean temperature control is not a uniformity certificate |
| Dropbox: PET Engenharia Elétrica UFC, *Apostila de MATLAB 8.1*, chs. 14–15 | Transfer functions, Bode/margin and Simulink blocks | `matlab/assess_fixed_pid_robustness.m` (not MATLAB-runtime-tested) |
| Dropbox: UERJ *Curso de MATLAB 5.1*, 2nd ed. | Numerical modeling, least squares and ODE methods | Supplemental study reference, not a direct code source |

**Source hierarchy:** the 2021 thesis remains authoritative for its reported models and quantitative claims. Earlier drafts, extracted formulas and independently chosen numerical algorithms are not silently merged into the thesis record. The 2004 De Luca study is a master's dissertation according to its own title page (the thesis bibliography labels it differently). No privately sourced PDF is versioned in Git.
