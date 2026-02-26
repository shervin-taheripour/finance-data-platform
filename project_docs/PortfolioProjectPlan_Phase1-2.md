# Portfolio Project Plan — Phase 1–2 Execution Guide (February 2026)

This document is the tactical companion to GlobalCareerStrategy_Shervin_updated.md.  
It defines the project sequence, features, and commercial framing for the 5 portfolio projects.

---

## Re-evaluation: Commercial & Contract Potential

| Project | Portfolio signal | Contract magnet? | Product/SaaS potential | Commercial verdict |
|---|---|---|---|---|
| **forestplotx** | Moderate (niche stats) | ⚠️ Low — solves a real pain point but in a small community (medical stats, meta-analysis researchers) | ⚠️ Open-source library, not a product. Could generate consulting leads from pharma/CROs | **Low commercial, high credibility signal** |
| **finance-data-platform** | High (DE + finance) | ✅ Moderate — demonstrates exactly what a contract client would hire you to build | ❌ Not a product; it's a showcase | **Contract-enabling, not revenue-generating** |
| **Config-driven stats pipeline** | High (automation + stats) | ✅✅ High — this IS a contract deliverable. "I built a config-driven pipeline that automates statistical analysis" is something companies pay for | ⚠️ Could become a productized consulting offer (you configure it for their data) | **Strongest contract magnet** |
| **Business Plot Assistant** | Moderate (ML + UX) | ⚠️ Low as a contract signal | ✅✅ **Highest product potential.** Color-theory + ML plot recommendation is a gap in the market. Tableau, PowerBI, Plotly — none do this well. Could be a standalone tool, API, or plugin | **Highest upside, highest risk, longest timeline** |
| **Trading pipeline** | Very high (DE + DS + finance) | ✅ Moderate — impressive but most finance firms build proprietary; they'd hire you for the skills, not the tool | ❌ Regulatory and data-licensing issues make this hard to productize | **Best "hire me" project for finance roles** |

---

## Execution Order & Expanded Specs

---

### 1. forestplotx — "The Python Forest Plot That Actually Works"

**Status: ✅ SHIPPED (v1.0.2)**

**Timeline:** Completed in ~5 days (originally budgeted weeks 1–2).

**What was delivered:**
- Publication-ready forest plot package supporting logistic, gamma, linear, and ordinal regression models
- Deterministic 4-case layout presets with explicit transformation contracts
- 116 tests, CI via GitHub Actions, PyPI-published
- DESIGN.md with auditable trade-off documentation
- RELEASE.md with full release checklist
- Before/after comparison images for promotion

**Promotion status (in progress):**
- LinkedIn post: drafted, scheduled for Monday 10:00
- r/Python post: drafted, scheduled for Wednesday/Thursday
- r/statistics post: planned for following week
- Tutorial notebook: planned for weeks 3–4
- CV bullet updated in DE language

**Links:**
- GitHub: https://github.com/shervin-taheripour/forestplotx
- PyPI: https://pypi.org/project/forestplotx/

---

### 2. finance-data-platform — "Layered Financial Data Platform"

**Timeline:** Weeks 2–5 (~3 weeks)

**Approach: New repo (hybrid).** This is a clean-architecture rebuild, not an upgrade of the original stock-analysis-tool capstone. Valuable domain logic (CAPM, indicators, ingestion patterns) is ported from the original project into a properly engineered platform. The original repo remains as-is (archived or private), credited in the README as the prior exploration.

**Why new repo instead of upgrade:**
- Original repo is 98% Jupyter Notebook — fundamentally wrong signal for DE
- Co-authorship makes ownership ambiguous in git history
- Architecture-first design requires a clean foundation
- The narrative is stronger: "I took a certification capstone and re-engineered it as a production-grade platform"

**MVP Scope (ships in ~3 weeks):**

| Layer | In MVP | Details |
|---|---|---|
| **Ingestion** | ✅ | yfinance connector (OHLCV, dividends, splits, metadata). Idempotent, retry-aware, schema-validated via Pydantic. |
| **Storage** | ✅ | Raw → staged → curated zone pattern using Parquet. DuckDB as analytical query layer on top. Local filesystem structured to mirror cloud object stores. |
| **Transforms** | ✅ | Technical indicators (SMA, EMA, RSI, MACD, rolling volatility, rolling correlation). Modular Python functions, not notebooks. |
| **Analysis** | ✅ (one module) | CAPM + portfolio metrics (beta, alpha, Sharpe, Treynor). Strongest existing analysis, directly recruiter-relevant for finance. |
| **Reporting** | ✅ (minimal) | Auto-generated HTML report via Jinja2 templates with key metrics and charts. Reproducible. |
| **Orchestration** | ✅ | Airflow DAG chaining ingest → store → transform → analyze → report. Single most important DE signal. |
| **Docker** | ✅ | docker-compose.yml bringing up full pipeline (app + Airflow) with one command. |
| **Tests** | ✅ | Unit tests for transforms and ingestion. Integration test for full pipeline run. |
| **CI** | ✅ | GitHub Actions: lint, test, build on push/PR. |
| **Docs** | ✅ | README with architecture diagram (Mermaid initially, Lucidchart upgrade optional later), quickstart, tech stack rationale, sample output. DESIGN.md with trade-off documentation. |

**Deferred (to project #4 or later iterations):**

| Feature | Why deferred |
|---|---|
| Alpha Vantage connector | One source proves the pattern; adding more is incremental |
| Finnhub connector | Commonly used in finance DE — worth adding post-MVP to show multi-source ingestion capability |
| FRED macro data connector | Scope control — macro data enrichment is a later feature |
| Options pricing, Monte Carlo VaR | DS-heavy — impressive but not MVP for DE signal |
| ML models (LSTM, XGBoost) | Hard boundary — this is project #4 territory |
| Streamlit dashboard | Wrong signal — dashboards read as DS, not DE. The auto-generated report replaces this |
| dbt transformation layer | Airflow is more visible as orchestration. dbt can be added in a later iteration |
| Cloud deployment (S3, actual Airflow cluster) | Cost/complexity — local structure mirrors cloud patterns; actual deployment is stretch |
| Spark | Overkill for this data volume. Mention in DESIGN.md as scaling option |

**Tech stack:**

| Layer | Tool | Rationale |
|---|---|---|
| Language | Python 3.11+ | Industry standard for DE and finance |
| Ingestion | yfinance + custom connector module | Free, reliable. Custom wrapper proves connector-building skill |
| Validation | Pydantic | Schema validation on ingest — standard in modern Python DE. Shows data contract thinking |
| Storage format | Parquet | Columnar, compressed, industry standard. Compatible with cloud object stores |
| Analytical DB | DuckDB | Embedded, reads Parquet natively, SQL interface. No server to manage. Increasingly adopted in finance/analytics |
| Transforms | Pure Python (pandas + numpy) | Portable, testable, no framework lock-in |
| Orchestration | Airflow (via Docker) | Most recognized orchestration tool in DE job descriptions, especially in finance/banking |
| Containerization | Docker + docker-compose | Full reproducibility, one command to run everything |
| Testing | pytest | Standard |
| CI | GitHub Actions | Standard, free, visible via badge |
| Reporting | Jinja2 → HTML | Templated report generation — shows artifact production, not just data storage |

**Repo structure:**

```
finance-data-platform/
├── src/
│   └── finance_data_platform/
│       ├── __init__.py
│       ├── ingestion/
│       │   ├── __init__.py
│       │   ├── yfinance_connector.py
│       │   └── schemas.py
│       ├── storage/
│       │   ├── __init__.py
│       │   └── parquet_store.py
│       ├── transforms/
│       │   ├── __init__.py
│       │   ├── indicators.py
│       │   └── enrichment.py
│       ├── analysis/
│       │   ├── __init__.py
│       │   └── portfolio.py
│       └── reporting/
│           ├── __init__.py
│           ├── generator.py
│           └── templates/
│               └── report.html
├── orchestration/
│   ├── dags/
│   │   └── finance_pipeline_dag.py
│   └── docker-compose.airflow.yml
├── tests/
│   ├── test_ingestion.py
│   ├── test_transforms.py
│   ├── test_analysis.py
│   └── test_pipeline_integration.py
├── data/                                # .gitignored; created by pipeline
│   ├── raw/
│   ├── staged/
│   └── curated/
├── docs/
│   ├── architecture.md
│   └── DESIGN.md
├── output/                              # .gitignored; generated reports
├── examples/
│   └── sample_report.html
├── .github/
│   └── workflows/
│       └── ci.yml
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── Makefile
├── README.md
├── CHANGELOG.md
└── LICENSE
```

**What a recruiter sees:** A layered financial data platform with proper engineering: modular code, orchestration, data lake zones, schema validation, containerized reproducibility, CI, and documentation. This person builds production-grade data infrastructure in the finance domain.

**Boundary with project #4 (Trading Pipeline):** This project = platform infrastructure. Project #4 = advanced analytics + ML on top of this platform. The architecture makes extension natural, but the MVP doesn't include it.

**What NOT to do:** Don't add ML models, trading strategies, or interactive dashboards. Don't use Spark. Don't try to add dbt and Airflow simultaneously. Keep it clean and engineering-focused.

---

### 3. Config-driven Statistical Pipeline — "Automated Analysis, Zero Custom Code Per Study"

**Timeline:** Weeks 5–8 (medium complexity)

**The concept:** A pipeline where you define a YAML/JSON config file specifying your dataset, variables, and desired statistical methods — and the system runs the full workflow from EDA to model results with formatted output including your custom forest plots.

**Features for impact:**

- **Config schema:** Well-documented YAML structure. Example:
  ```yaml
  dataset: path/to/data.csv
  outcome: treatment_response
  grouping: study_site
  methods:
    - glmm
    - gamma_regression
    - propensity_score_matching
  output:
    - summary_table
    - forest_plot
    - diagnostics
  ```
- **Method library:** GLMM, gamma regression, PSM, and at least one more (e.g., Cox PH or meta-analysis). Each method implemented as a pluggable module with a consistent interface.
- **EDA module:** Automatic descriptive statistics, missingness report, distribution checks — generated before any modeling runs.
- **Output layer:** Formatted tables (LaTeX/HTML/CSV), forest plots via forestplotx (your own library — cross-pollination), diagnostic plots.
- **Python + R bridge:** Use rpy2 or subprocess calls for R-native methods where Python equivalents are weak. Document this clearly — it shows pragmatism over dogma.
- **Reproducibility:** Logged runs with config snapshots, random seeds, environment info. A re-run with the same config produces identical output.

**What a recruiter sees:** Automation engineering applied to statistics. Config-driven design is a pattern recognized from DE (Airflow, dbt, Terraform). Signals: "this person thinks in systems, not one-off scripts."

**Commercial angle:** Strongest contract magnet. Pharma companies, CROs, insurance analytics teams run repetitive statistical analyses across studies. A config-driven pipeline that standardizes this is directly valuable. Productized consulting potential.

---

### 4. Trading Pipeline — "Full Reproducible Finance Pipeline: Ingestion to Report"

**Timeline:** Weeks 8–14 (high complexity, start during Phase 2)

**Relationship to finance-data-platform:** This is the advanced evolution. finance-data-platform shows you can build a data platform; the trading pipeline shows you can build serious analytics on top of it with production-grade practices.

**Features for impact:**

- **Multi-source ingestion:** Add Alpha Vantage, Finnhub, and FRED connectors to the platform
- **Storage evolution:** Delta Lake format or S3-compatible layer (MinIO locally)
- **Advanced transforms:** OHLCV enrichment with options-derived metrics, cross-asset correlations
- **Analysis layer:** Monte Carlo VaR, portfolio optimization (mean-variance), options pricing, and one ML component (e.g., XGBoost for return prediction). Each as a modular, swappable component.
- **Orchestration:** Extended Airflow DAGs with branching, retries, and monitoring
- **Reporting:** Auto-generated PDF report with full analytics output
- **Testing:** Comprehensive unit + integration tests
- **Documentation:** Full architecture diagram, tech stack rationale document

**What a recruiter sees:** The project that gets you hired at a London FinTech or Zurich quant desk. Demonstrates every layer of a modern data platform in the exact domain they care about.

**Scope management:** Define an MVP (extend platform with one new source + one advanced analysis + report) and publish that first. Add layers incrementally.

---

### 5. Business Plot Assistant — "Intelligent Visualization Recommendations"

**Timeline:** Defer to post-June (or parallel lightweight scoping only)

**Why defer execution but invest in scoping:** Highest product ceiling of any project. The gap in the market is real — no major tool does ML-based plot type + color palette recommendation well. But execution complexity is high and payoff timeline extends beyond the 4-month window.

**Product concept (for future development):**

- **Input:** User provides dataset (or describes variables) and context (presentation, report, dashboard, print).
- **Recommendation engine:** Suggests plot type based on data shape + perceptual research + context. Rule-based + ML hybrid.
- **Color palette engine:** Generates palettes based on color theory, accessibility (colorblind-safe), and context.
- **Output:** Rendered plot with recommended settings, exportable. Optional code snippet.

**Commercial potential:**

- Plugin/API model: Tableau extension, PowerBI custom visual, or standalone API
- Target buyers: enterprise analytics teams, consulting firms, media/publishing companies
- Competitive gap: Tableau's "Show Me" is rule-based and limited. No tool combines ML plot recommendation with color theory.

**What to do now (Phase 1–2):** Write a 1-page product brief. Define MVP scope. Don't build yet.

---

## Summary Table

| # | Project | Weeks | Status | Primary value | Secondary value |
|---|---|---|---|---|---|
| 1 | forestplotx | 1–2 | ✅ Shipped (v1.0.2) | Credibility signal, shows you ship | Pharma/CRO consulting leads |
| 2 | finance-data-platform | 2–5 | 🔄 Starting now | Portfolio anchor for DE in finance | Contract-enabling showcase |
| 3 | Config-driven stats pipeline | 5–8 | Queued | Strongest contract magnet, dual DE/DS signal | Productized consulting potential |
| 4 | Trading pipeline | 8–14 | Queued | Highest-impact finance DE project | "Hire me" project for London/Zurich |
| 5 | Business Plot Assistant | Post-June | Scoping only | Highest product/SaaS ceiling | Scope now, build later |

---

## Current Focus

**Project #2: finance-data-platform** — MVP in ~3 weeks. Architecture-first, engineering-focused, finance-domain. See project section above for full scope, tech stack, and repo structure.

---

This document is a living tactical plan. Review at each project completion and adjust timelines based on actual pace and energy levels. If mood destabilizes, freeze at the last published project and defer to Stabilization mode per LifeSystem_Master.
