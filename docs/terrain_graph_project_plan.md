# Terrain Graph Pipeline Modernization – Project & Tasking Plan

*Version 0.2 — 2025‑04‑18*

---

## 1 · Purpose
Establish a scalable, maintainable pipeline that produces:
1. **Master PostGIS + pgRouting graph** (roads + water‑buffer + terrain) for continental extents.
2. **On‑demand AOI slices** (GraphML **and** Valhalla tiles) sized for up to a **1‑hour drive (~45 mi/72 km highway equivalent)** during initial testing, extensible to 24‑hour scenarios.
3. Automation tooling (Typer CLI + Makefile + nightly cron) and documentation to enable both scheduled and ad‑hoc builds.

## 2 · Success criteria
| Metric | Target |
|---|---|
| AOI slice ≤ 1 h drive | < 250 MB GraphML / < 25 MB Valhalla tiles |
| AOI slice ≤ 24 h drive | Fits on 64 GB RAM laptop (*stretch goal – validated via benchmark*) |
| Slice export latency | < 2 min on GCP VM (1 h AOI) |
| Nightly rebuild window | < 4 h for one continent |
| Code health | 90 % pytest coverage; flake8 clean |

## 3 · Deliverables
| ID | Artifact | Owner | Due |
|---|---|---|---|
| D1 | `docker-compose.yml` (PostGIS 16 + pgRouting 3.6) | Backend | W2 |
| D2 | `sql/` – water_buffer, terrain_grid, topology fns | Backend | W3 |
| D3 | `export_slice.py` Typer CLI (+ Valhalla option) | Backend | W4 |
| D4 | `Makefile` targets & cron script | DevOps | W4 |
| D5 | Validation notebooks & pytest suite | QA | W5 |
| D6 | Ops run‑book & user guide (Markdown) | Tech Writer | W6 |
| D7 | **`bench_memory.py` benchmark harness** | QA | W5 |

## 4 · Work Breakdown Structure (WBS)
| WBS | Task | Notes | Depends |
|---|---|---|---|
| 1.0 | **Environment** | | |
| 1.1 | Provision GCP high‑RAM VM (Ubuntu 22 LTS) | 64 vCPU, 256 GB RAM, 2 TB NVMe | – |
| 1.2 | Docker host hardening & backup plan | Enable WAL archiving | 1.1 |
| 2.0 | **Data ingest** | | |
| 2.1 | Download Geofabrik PBFs (continent) | Nightly cron | 1.2 |
| 2.2 | `osm2pgsql --flex` load | 8× parallel | 2.1 |
| 3.0 | **DEM mosaic** | | |
| 3.1 | Load global SRTM 30 m COGs | raster2pgsql | 1.2 |
| 3.2 | Load regional high‑res DEMs (10 m / 3 m) | when available | 3.1 |
| 3.3 | Build `dem_best` & `dem_best_slope` views | materialised daily | 3.2 |
| 4.0 | **Graph construction SQL** | | 2.x, 3.x |
| 4.1 | Water polygon buffer generator (param: buf m) | `build_water_buffers()` | |
| 4.2 | Terrain grid generator (param: profile) | hex grid + slope cost | 4.1 |
| 4.3 | Unified topology & cost columns | pgr_CreateTopology | 4.2 |
| 5.0 | **Export tooling** | | 4.x |
| 5.1 | `export_slice.py` — GraphML path | nearest node → isochrone → slice | |
| 5.2 | Valhalla tile export option | call `valhalla_build_tiles` | 5.1 |
| 5.3 | Unit tests & benchmark harness | pytest + timeit | 5.1 |
| 5.4 | **`bench_memory.py`** – memory & size profiling | 1 h → 24 h AOIs | 5.1 |
| 6.0 | **Deployment & Ops** | | 5.x |
| 6.1 | Docker Compose for local dev (mac) | pgAdmin included | |
| 6.2 | Crontab for nightly rebuild | `make rebuild-all` | 4.x |
| 6.3 | Ad‑hoc CLI docs | usage examples | 5.x |
| 7.0 | **Code audit & migration** | | parallel |
| 7.1 | Inventory existing Python repo | identify reusable modules | – |
| 7.2 | Map functions to new pipeline stages | note gaps | 7.1 |
| 7.3 | Refactor / deprecate old code | keep tests green | 7.2 |

## 5 · Timeline (6‑week initial sprint)
```
W1  ████ Env + PBF ingest
W2  ████ DEM & SQL fns draft
W3  ████ Graph build end‑to‑end
W4  ████ Export CLI + Valhalla
W5  ████ Test/benchmark + Docs
W6  ████ Buffer to prod + hand‑off
```

## 6 · Risks & mitigations
| Risk | Impact | Mitigation |
|---|---|---|
| 24 h slice exceeds 64 GB RAM | High | Early bench harness; option to fall back to Valhalla tiles |
| High‑res DEM licensing | Med | Keep sourcing table w/ licence flags; allow build w/o restricted DEM |
| Team unfamiliar w/ pgRouting | Med | Schedule workshop; pair program first SQL functions |

## 7 · Benchmark AOI test cases
| Label | Approx centre (lon, lat) | Notes |
|---|---|---|
| **LA‑Contrail** | ‑92.95, 31.14 | Region around Fort Johnson/JRTC in western Louisiana |
| **IA‑Central** | ‑93.63, 41.99 | Iowa State → rural & interstate mix |
| **IA‑West** | ‑95.86, 41.26 | Council Bluffs / Omaha approaches |
| **CA‑NTC** | ‑116.68, 35.31 | Fort Irwin & National Training Center desert |

These will seed the default runs in `bench_memory.py`.

---

## 8 · Next Steps
1. **Verify AOI centres** above (adjust lon/lat if needed).
2. Assign owners to deliverables D1‑D7.
3. I’ll proceed with code audit (7.1) and initial benchmark script.

