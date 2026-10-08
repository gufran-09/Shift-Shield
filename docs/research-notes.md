# Research notes and provenance

## NIOSH work/rest and clothing source

**Primary source:** National Institute for Occupational Safety and Health (NIOSH), *Criteria for a Recommended Standard: Occupational Exposure to Heat and Hot Environments*, DHHS (NIOSH) Publication No. 2016-106 (2016). Official PDF: <https://www.cdc.gov/niosh/docs/2016-106/pdfs/2016-106.pdf>; publication record: <https://www.cdc.gov/niosh/publications/numbered/2016-106.html>.

- Printed page 70, Table 5-1: NIOSH comparison values by workload: resting 33°C (≤100 kcal/h); light 30°C (<200 kcal/h); moderate 28°C (201–300 kcal/h); heavy 26°C (301–400 kcal/h); very heavy 25°C (401–500 kcal/h). These are acclimatized-worker exposure limits, not a full four-band work/rest schedule.
- Printed page 94, Figure 8-1: RAL curves for unacclimatized workers; axes WBGT vs metabolic heat; four plotted work durations (15, 30, 45, 60 minutes per hour).
- Printed page 95, Figure 8-2: REL curves for acclimatized workers, with the same axes and work durations.
- These two figures are graphical, not a tabular machine-readable lookup. The product config labels derived values as a conservative digitization of the curve, records workload/point selection and rounding, and remains marked as pending occupational-safety review. It does not cite NIOSH's unrelated adjusted-air-temperature/EPA example tables (Tables 6-2 and 6-3, printed p.76) as WBGT thresholds.
- Printed page 19, Table 3-2: 2006 clothing WBGT adjustments: work clothing baseline 0°C; cloth coveralls 0°C; double-layer cloth 3°C; SMS coveralls 0.5°C; polyolefin coveralls 1°C; limited-use vapor-barrier coveralls 11°C. The report separately notes recommended corrections for two-layer clothing and partially air/vapor-impermeable protective ensembles, and that WBGT is not appropriate for fully impermeable encapsulating ensembles. Do not treat generic “heavy/impermeable PPE” labels as exact garment equivalence.
- Executive summary printed page vi: one 8-oz cup of water or other fluid every 15–20 minutes, presented as general cited guidance, not individualized medical advice.

## Published WBGT calculation method

B. Lemke and T. Kjellstrom, “Calculating Workplace WBGT from Meteorological Data,” *Industrial Health* 50 (2012), 267–278: <https://www.jniosh.johas.go.jp/en/indu_hel/doc/IH_50_4_267.pdf>. The authors assess meteorological-input WBGT methods and recommend Liljegren for outdoor calculations; they discuss limitations for indoor/no-solar use and identify Bernard as a better fit there. This supports the method selection, but the supplied ShiftShield PDF remains the controlling project specification.

`pywbgt` project: <https://github.com/kwodzicki/pywbgt>; package pinned in PyPI metadata as 3.0.7. The project documents Liljegren (2008), Dimiceli (2013), and Bernard/Pourmoghani (1999) implementations; inputs include time/location, solar, pressure, air temperature, dew point and wind. It is GPL-3.0 and includes C/Cython components requiring a C compiler and OpenMP. Run Lambda-target build/import/reference checks and preserve license/notice information. Do not switch algorithms silently on build failure.

ECMWF `thermofeel` WBGT docs: <https://thermofeel.readthedocs.io/en/latest/guide/wbgt.html>; package overview/license: <https://thermofeel.readthedocs.io/>. Its WBGT formulation uses a De Dear globe-temperature estimate plus an Australian Bureau of Meteorology WBGT approximation and Stull wet-bulb method; it is an available comparison but is not the selected primary physical method. Apache-2.0 license.

## Forecast source

Open-Meteo API documentation: <https://open-meteo.com/en/docs>. It exposes air temperature, relative humidity, 10 m wind, shortwave, direct and diffuse radiation; the usual forecast variables are hourly and should be interpolated to 15-minute schedule intervals with upstream resolution disclosed. Historical archive forecasts/reanalysis have their own provenance and may differ from station observations.

## Site specificity evidence

The ShiftShield v7 plan cites an ASU field comparison in which on-site WBGT was approximately 2.4–2.5°C above regional-station estimates and the tested surface-type differences were largely insignificant. Relevant research identified during review:

- A. Grundstein et al. (2020), comparison of WBGT across surfaces: <https://pmc.ncbi.nlm.nih.gov/articles/PMC7353887/>.
- H. Guyer et al. (2021), “Identifying the need for locally-observed wet bulb globe temperature,” *Environmental Research Letters*: <https://iopscience.iop.org/article/10.1088/1748-9326/ac32fb>.

The plan’s shade, surface, land-use and wind numbers are explicitly called starting assumptions, not cited calibration constants. Keep them in a versioned demo configuration and disclose uncertainty; the model is not a substitute for a site sensor or occupational review.

## Hackathon source constraints

`ShiftShield_Final_Plan_v7.pdf`, internal team plan prepared October 5, 2026, says code/repository begin at Oct 8 kickoff, and requires the repository history to match those event dates. Initial scaffold commit recorded at `2026-10-08 06:37:19 +0000`. This project's Git history must remain chronological; do not import pre-kickoff code or claim non-existent AWS deployments, field validations, approved action plans, or worker outcomes.


## Site-microclimate study details verified

Grundstein & Cooper (2020), “Comparison of WBGTs over Different Surfaces within an Athletic Complex,” *Medicina* 56(6):313, DOI 10.3390/medicina56060313, full text: <https://pmc.ncbi.nlm.nih.gov/articles/PMC7353887/>. Four-day study across grass, artificial turf and hardcourt tennis in humid subtropical conditions. The surface-type WBGT difference was not statistically significant in morning, midday or afternoon (midday p=0.776); WBGT still changed rapidly with solar radiation, and dry-bulb/dewpoint differed by surface. This does not prove surface irrelevance in other climates or sites. It supports keeping a surface coefficient small/provisional and giving direct solar/shade greater explanatory weight.

Guyer et al. (2021), “Identifying the need for locally-observed wet bulb globe temperature across outdoor athletic venues for current and future climates in a desert environment,” *Environmental Research Letters*, DOI 10.1088/1748-9326/ac32fb; article: <https://iopscience.iop.org/article/10.1088/1748-9326/ac32fb>, metadata: <https://iopscience.iop.org/article/10.1088/1748-9326/ac32fb/meta>. Search-result text and the supplied Plan v7 cite on-field WBGT averaging about 2.4–2.5°C higher than regionally estimated WBGT. The publisher page currently returned a CAPTCHA, so do not generalize that study-specific magnitude beyond the source/context or treat it as a universal correction.

## Strands Agents SDK

Official Python SDK quickstart: <https://strandsagents.com/docs/user-guide/sdk/quickstart/overview/>. Strands is a library running inside the service, not a hosted platform. Basic Python interface: `from strands import Agent; response = Agent()(prompt)`.

Official `Agent` API: <https://strandsagents.com/docs/api/python/strands.agent.agent/>. The Python SDK accepts a Pydantic model via `agent.structured_output(output_model, prompt)` or `agent(prompt, structured_output_model=Model)`; result includes structured output. Use this only for candidate rule extraction, then independently verify quote/page in deterministic code.

Official Amazon Bedrock model provider: <https://strandsagents.com/docs/user-guide/sdk/model-providers/amazon-bedrock/>. Instantiate `BedrockModel(model_id=..., region_name=...)`; required non-streaming IAM action is `bedrock:InvokeModel` and streaming also needs `bedrock:InvokeModelWithResponseStream`. Use Lambda role credentials and scope model resources; never put credentials in frontend/repo. This session has no AWS role/model access configured.

## Local package smoke test

Installed pinned `pywbgt==3.0.7` under Python 3.12 with C/Cython + OpenMP dependencies and exercised `method="liljegren"` with 38°C dry bulb, 22°C dewpoint, 1000 hPa, 650 W/m², 2 m/s, Delhi coordinates, 2025-05-20 13:00 UTC. Observed library components: `Tg≈47.69°C`, `Tnwb≈27.31°C`, library `Twbg≈32.46°C`, demonstrating API/build viability in this Sandbox only. The project code combines `Tnwb`, `Tg`, and `Tdb` explicitly using the supplied outdoor/indoor formula. This is not validation of Lambda build compatibility or field accuracy.
## Integration finding — pywbgt input mutation (2026-10-08)

- Upstream package: [`pywbgt` 3.0.7, kwodzicki/pywbgt](https://github.com/kwodzicki/pywbgt), installed from PyPI and checked by direct source inspection and a reproducible runtime sample.
- The Liljegren wrapper exposes adjusted solar irradiance and 2 m wind in its output tuple and can mutate input NumPy arrays in place during calculation. With representative inputs `S_site=937.5 W/m²` and `u_site=1.5 m/s`, the library returned adjusted solar about `401.343 W/m²` and 2 m wind about `1.340 m/s`; passing shared arrays could overwrite logged raw inputs.
- The adapter now passes copies of all model inputs and records site-adjusted 10 m inputs separately from model-derived radiation/wind outputs. Regression `test_liljegren_reference_and_raw_site_inputs_are_preserved` fixes this behavior. This is an integration note, not a change to the published Liljegren method.
