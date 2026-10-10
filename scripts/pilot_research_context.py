"""Pilot research, part 2 (2026-10-10): fill the context dimensions that part 1 left empty (demand, finance, regulation, geopolitics/security,
technology). APPENDS to the existing research.json files (idempotent: topics and claims already present are skipped). Do NOT re-run
pilot_research.py afterwards: it regenerates the records from scratch and would drop these additions.
Provenance: 'page opened' = the page was read in full; 'search summary only' = only the search-result summary was seen."""
from pathlib import Path

from parlwatch.research.render import to_markdown
from parlwatch.research.schema import Check, Claim, Finding, Research, Source, Topic

TODAY = "2026-10-10"
OPENED, SNIP = "page opened", "search summary only, page not opened"


def S(title, url, tier, note):
    return Source(title=title, url=url, tier=tier, accessed=TODAY, note=note)


NEXTWEB = S("The Next Web: Alphabet, Amazon, Meta Q1 2026 earnings (AI cloud)", "https://thenextweb.com/news/alphabet-amazon-meta-q1-2026-earnings-ai-cloud", "secondary", OPENED + "; relays company results")
REGISTER = S("The Register: Europe's sovereign cloud spend set to triple (Gartner, 9 Feb 2026)", "https://www.theregister.com/2026/02/09/europe_sovereign_cloud_spend", "secondary", OPENED)
DCD_GARTNER = S("DatacenterDynamics: Europe sovereign cloud spending to triple 2025-2027 (Gartner)", "https://www.datacenterdynamics.com/en/news/europe-spending-on-sovereign-cloud-infrastructure-to-triple-from-2025-2027-gartner/", "secondary", SNIP + "; says governments remain the main buyers, which differs from The Register")
SP = S("S&P Global: European data centre power demand to double by 2030 (30 Jul 2025)", "https://www.spglobal.com/energy/en/news-research/latest-news/electric-power/073025-european-data-center-power-demand-to-double-by-2030-straining-grids", "secondary", SNIP)
ITBRIEF = S("DataCentreNews UK: AI data centre demand to exceed supply by 2030", "https://datacentrenews.uk/story/ai-data-centre-demand-to-exceed-supply-by-500-by-2030", "weak", SNIP + "; industry trade report, figures (AI = 38% of 2026 demand) not traced to a primary dataset")
CDE = S("Connaissance des énergies: data centres in France, how much electricity to come (ADEME study, Jan 2026)", "https://www.connaissancedesenergies.org/data-centers-en-france-quelle-consommation-delectricite-venir", "secondary", OPENED + "; page confirms RTE's +10 TWh by 2030 and that connected data centres use ~20% of contracted capacity")
OPERA = S("Opera Énergie: la France sous-estime l'impact de l'IA sur la transition énergétique", "https://opera-energie.com/media/france-sous-estime-impact-ia-transition-energetique/", "weak", SNIP + "; the ~45 TWh by 2030 versus 23-28 TWh in 2035 comparison came from the search summary and which result carried it is not certain")
AIWEEKLY = S("AI Weekly: Amazon, Microsoft, Alphabet, Meta plan $725B AI capex in 2026", "https://aiweekly.co/node/8566", "weak", SNIP + "; other sources give totals from $470bn to $830bn")
OVH_GUID = S("OptionFinance: OVHcloud confirms its annual objectives (25 Jun 2026)", "https://www.optionfinance.fr/info-financiere-en-continu/d/2026-06-25-ovhcloud-porte-par-le-cloud-public-confirme-ses-objectifs-annuels.html", "secondary", SNIP + "; capex 33-35% of revenue, organic growth 5-7%")
INVESTAI = S("DatacenterDynamics: EU allocates €20bn to four AI gigafactories", "https://datacenterdynamics.com/en/news/eu-allocates-20bn-to-developing-four-ai-gigafactories", "secondary", SNIP + "; announced Feb 2025, selection outcome not found")
COMM_CLOUD = S("European Commission: Commission advances cloud sovereignty through strategic procurement (17 Apr 2026)", "https://commission.europa.eu/news-and-media/news/commission-advances-cloud-sovereignty-through-strategic-procurement-2026-04-17_de", "primary", OPENED)
CADA = S("Covington Inside Global Tech: the EU Cloud and AI Development Act in depth (11 Jun 2026)", "https://www.insideglobaltech.com/2026/06/11/the-eu-cloud-and-ai-development-act-in-depth/", "secondary", OPENED + "; law-firm note, the Commission's own text was not opened")
HL_EUCS = S("Hogan Lovells: EUCS, data sovereignty issues drive debate on the EU cloud certification scheme", "https://hlc.com/en/publications/eucs-controversial-data-sovereignty-issues-continue-to-drive-debate-around-the-eu-certification-scheme-for-cloud-services", "secondary", SNIP + "; says the EU-headquarters requirement for the highest level was dropped from the 2024 draft")
SOTA = S("sota.io: EUCS cloud assurance levels 2026", "https://sota.io/blog/eucs-cloud-assurance-levels-which-providers-qualify-eu-sovereignty-2026", "weak", SNIP + "; developer blog, the 'not formally adopted as of mid-2026' status needs an official source")
SECNUM = S("Ayinedjimi Consultants: SecNumCloud 2026 and EUCS", "https://ayinedjimi-consultants.fr/articles/secnumcloud-2026-eucs", "weak", SNIP + "; says SecNumCloud 3.2 adds immunity criteria against non-EU law; ANSSI's referential itself was not opened")
OVH_SNC = S("OVHcloud corporate: SNC Cloud Platform obtains SecNumCloud qualification (1 Sep 2026)", "https://corporate.ovhcloud.com/en/newsroom/news/ovhcloud-obtains-secnumcloud-qualification-snc-cloud-platform/", "primary", SNIP + "; mentions the 14 Apr 2026 decree under Law 2024-449")
MS_SENATE = S("Génération NT: Microsoft, European data and the Cloud Act (Senate hearing, June 2025)", "https://www.generation-nt.com/actualites/microsoft-donnees-europe-souverainete-cloud-loi-2060822", "secondary", OPENED)
EXPORT = S("Science|Business: European AI ecosystem worried about new US export restrictions", "https://sciencebusiness.net/news/ai/european-ai-ecosystem-worried-about-new-us-export-restrictions", "secondary", SNIP + "; Jan 2025 rules covering 17 EU member states")
CASRAI = S("CASRAI: the AI chip export control landscape in 2026", "https://casrai.org/news/ai-chip-export-controls", "weak", SNIP + "; says the 2025 diffusion rule was rescinded and a Jan 2026 rule set thresholds and end-use certification; verify against US government text")
STAR = S("The Star (wire): France's Mistral announces new AI model (6 Oct 2026)", "https://www.thestar.com.my/tech/tech-news/2026/10/06/france039s-mistral-announces-new-ai-model", "secondary", OPENED)
CYBERNEWS = S("Cybernews: Mistral unveils 'Le Chonk' as alternative to top AI models from China and the US", "https://cybernews.com/news/mistral-sovereign-model-le-chonk/", "secondary", SNIP + "; the model-size and independent-index figures (Chinese model 46 vs Mistral 38) are from search summaries and unconfirmed")
CN_OPEN = S("Tech-Insider: DeepSeek and Qwen top Hugging Face in 2026", "https://tech-insider.org/nl/deepseek-qwen-hugging-face-top-2026/", "weak", SNIP + "; aggregator")
ORRICK = S("Orrick: Mistral €3B Series D at €21B post-money (Sept 2026)", "https://www.orrick.com/en/News/2026/09/Orrick-Advises-Mistral-in-its-3B-Series-D-at-21B-Post-Money-Valuation", "secondary", OPENED)
LCP_REPORT = S("LCP: le rapport de la commission d'enquête a été adopté", "https://lcp.fr/actualites/numerique-le-rapport-de-la-commission-d-enquete-sur-les-vulnerabilites-de-la-france-a", "secondary", SNIP)

F = Finding
SHARED_DEMAND_BEFORE = [
    F(date="2026-04", summary="Hyperscalers report demand above capacity. Alphabet's CEO says the company is 'compute constrained in the near term'; Google Cloud grew 63% year on year (about $20.0bn in the quarter), AWS 28% (about $37.6bn); Google Cloud's backlog is above $460bn, nearly double the previous quarter.", sources=[NEXTWEB]),
    F(date="2026-02-09", summary="Gartner: European sovereign-cloud infrastructure spending was about $6.9bn in 2025 and is forecast to grow 83% in 2026, then nearly double again in 2027; global spending about $80bn in 2026 (+35.6%). Drivers: the US CLOUD Act, tensions with the US, the Microsoft/ICC incident. Buyers per The Register: European enterprises (Airbus, Schwarz Group, financial firms), mostly for new workloads; another trade report says governments remain the main buyers, so sources disagree.", sources=[REGISTER, DCD_GARTNER]),
    F(date="2025-07-30", summary="S&P Global: European data-centre power demand expected to double by 2030, straining grids.", sources=[SP]),
]
SHARED_CAPEX = F(date="2026-04", summary="2026 capital-expenditure guidance: Alphabet $180-190bn (raised), Meta $125-145bn (raised), Amazon about $200bn (Microsoft's figure was not on the page). Totals quoted for the big four vary by source from $470bn to $830bn, so read them as an order of magnitude.", sources=[NEXTWEB, AIWEEKLY])
INVEST_F = F(date="2025-02", summary="EU InvestAI: target of €200bn of AI investment, including a €20bn fund for about four 'AI gigafactories' of roughly 100,000 latest-generation chips each. The outcome of the gigafactory selection was not found.", sources=[INVESTAI])
CADA_F = F(date="2026-06-03", summary="The Commission proposes the Cloud and AI Development Act. Public-sector cloud buyers would face four 'Union assurance levels' (1: data in the EU; 2: all operating staff and assets in the EU; 3: EU-owned and controlled; 4: no third-country control), a 'Union added value' criterion worth at most 15 of 120 points in procurement, and 'data centre acceleration zones' with a 12-month maximum permit time. It cites the EU cloud market share falling from about 29% (2017) to 15% (2022). Status: awaiting negotiation between Council and Parliament. A search summary says the Act aims to triple EU capacity in 5 to 7 years; the note I opened gives no number.", sources=[CADA])
MS_F = F(date="2025-06", summary="Microsoft France's director of legal and public affairs, questioned under oath by the French Senate, said he could not guarantee that French citizens' data would never be passed to US authorities without French approval: under the US CLOUD Act, a formal legal request must be answered wherever the data sits. He added this had not happened for a European entity according to Microsoft's transparency reports.", sources=[MS_SENATE])
EXPORT_F = F(date="2025-01", summary="US export controls on advanced AI chips: the January 2025 rules would have limited access for 17 EU member states and drew a protest from the Commission. A weak source says that rule was later rescinded and a January 2026 rule set performance thresholds and end-use certification; the current legal position for EU buyers needs an official source.", sources=[EXPORT, CASRAI])

# ------------------------------------------------------------------ Klaba
klaba = Research.model_validate_json(Path("data/meetings/19471620_6abccf18f0e48/research.json").read_text())
new_k = [
    Topic(id="demand", dimension="demand", title="Demand for compute and storage from industry at large",
          why_it_matters="Klaba asked whether AI demand is lasting and said OVHcloud concluded it is too risky not to invest. Whether capacity is scarce, who is buying it and how much power it needs decide whether the supply he describes is too small or too large.",
          before=[*SHARED_DEMAND_BEFORE,
                  F(date="2026-01", summary="France: RTE's December 2025 outlook adds about 10 TWh of data-centre consumption between 2024 and 2030. An ADEME study (6 Jan 2026) finds that data centres already connected use only about 20% of their contracted connection capacity, which suggests that connection requests overstate real demand. A weaker source says validated connection requests already equal about 45 TWh by 2030, far above the 23-28 TWh RTE had assumed for 2035.", sources=[CDE, OPERA]),
                  F(date="2026", summary="A trade report says AI is about 38% of data-centre demand in 2026 and could be most of it by 2030, with inference overtaking training. Not traced to a primary dataset.", sources=[ITBRIEF])]),
    Topic(id="finance", dimension="finance", title="Who is spending on infrastructure, and how much",
          why_it_matters="Klaba contrasted European champions with US hyperscalers; the gap in capital explains both his call for public procurement and his scepticism about gigawatt-scale sites.",
          before=[SHARED_CAPEX,
                  F(date="2026-06-25", summary="OVHcloud's own guidance for FY2026: capital expenditure of 33-35% of revenue (about €0.4bn on a revenue of about €1.15bn, my calculation), organic growth of 5-7%.", sources=[OVH_GUID]),
                  INVEST_F,
                  F(date="2026-04-17", summary="Scale comparison (my calculation): the EU sovereign-cloud contract is at most €180M over 6 years, i.e. at most €30M a year, against Amazon's roughly $200bn of 2026 capital expenditure alone: the contract is about 0.015% of one hyperscaler's annual spending.", sources=[COMM_CLOUD])]),
    Topic(id="reg_cloud", dimension="regulation", title="The regulatory framework for cloud and data centres",
          why_it_matters="Klaba's case for procurement preference, SecNumCloud and a sovereign market depends on what the rules require and what is still only proposed.",
          before=[F(date="2024", summary="EU cloud certification (EUCS): the draft dropped the requirement that a provider be headquartered in the EU for the highest level, after objections from member states and industry. A weak source says the highest level was still not formally adopted in mid-2026.", sources=[HL_EUCS, SOTA]),
                  F(date="2026-04-14", summary="France: a decree of 14 April 2026 implementing Law 2024-449 requires certified cloud services for sensitive State data. SecNumCloud 3.2 is ANSSI's referential; a weak source says it adds immunity criteria against non-EU law.", sources=[OVH_SNC, SECNUM]),
                  CADA_F]),
    Topic(id="geopolitics", dimension="geopolitics_security", title="Extraterritorial law and dependence on US suppliers",
          why_it_matters="The sovereignty argument in Klaba's hearing rests on who can compel access to data and on dependence for chips and cloud services.",
          before=[MS_F, EXPORT_F,
                  F(date="2026-02-09", summary="Gartner names the CLOUD Act, tensions with the US and the Microsoft/ICC incident as reasons why European organisations are shifting to sovereign cloud.", sources=[REGISTER])]),
]
added = []
for t in new_k:
    if t.id not in {x.id for x in klaba.topics}:
        klaba.topics.append(t)
        added.append(t.id)
if "K10" not in {c.id for c in klaba.claims}:
    klaba.claims.append(Claim(id="K10", speaker="Octave Klaba (speaker inferred from context)", time="01:15:26", kind="figure", topic="demand",
                              text="A cloud provider generates 15 to 20 million euros of revenue a year per megawatt.",
                              quote_fr="un cloud provider, il génère entre 15 et 20 millions d'euros par an avec un mégawatt",
                              checks=[Check(checkpoint="at_meeting", verdict="not_checked", checked_on=TODAY, evidence="Queued: no benchmark for revenue per megawatt of cloud capacity was researched yet.")],
                              next_step="Compare with data-centre industry benchmarks (revenue per MW for colocation, cloud and AI workloads)."))
klaba.queue += [q for q in [
    "Check the 15-20 M€ per MW figure (K10) against industry benchmarks.",
    "Read RTE's own publication on connection requests (15 GW; about 45 TWh by 2030) and the ADEME study on the 20% utilisation of contracted capacity.",
    "Confirm whether the Cloud and AI Development Act targets a tripling of EU capacity (search summary) or gives no number (law-firm note).",
    "Check whether the highest EUCS level has been formally adopted, from an official source.",
    "Find the outcome of the EU AI gigafactory selection (InvestAI).",
    "Open the Commission's own CADA text and ANSSI's SecNumCloud 3.2 referential.",
] if q not in klaba.queue]
klaba.method += "; context dimensions (demand, finance, regulation, geopolitics_security) added 2026-10-10"

# ------------------------------------------------------------------ Mensch
mensch = Research.model_validate_json(Path("data/meetings/18888392_6a0330a9d4404/research.json").read_text())
new_m = [
    Topic(id="demand", dimension="demand", title="Demand for AI compute and cloud from industry at large",
          why_it_matters="Mensch argued that AI will consume about 10% of Europe's payroll and that Europe must build compute for it. Whether demand outruns capacity, and how fast, is the premise of his case.",
          before=SHARED_DEMAND_BEFORE),
    Topic(id="finance", dimension="finance", title="Capital for compute: hyperscalers, EU funds and Mistral's own raises",
          why_it_matters="Mensch compared Europe's means with those of US and Chinese players and said Mistral invests about a billion in R&D this year.",
          before=[SHARED_CAPEX, INVEST_F,
                  F(date="2025-09", summary="Mistral's Series C: €1.7bn at a €11.7bn valuation.", sources=[ORRICK])],
          after=[F(date="2026-09-08", summary="Mistral's Series D: €3bn at €21bn post-money, led by Samsung with the Scaleup Europe Fund (EQT) and PSG. A wire report says Mistral plans 'very deep' partnerships with backers including ASML and Samsung and trained its latest model on its own infrastructure.", sources=[ORRICK, STAR])]),
    Topic(id="cada", dimension="regulation", title="The EU Cloud and AI Development Act",
          why_it_matters="Mensch asked for European preference in public procurement; the Commission's proposal, published three weeks after his hearing, is the main legislative answer so far.",
          after=[CADA_F]),
    Topic(id="geopolitics", dimension="geopolitics_security", title="Extraterritorial law, chips and dependence on US suppliers",
          why_it_matters="Mensch's argument that Europe must not be a mere consumer of AI rests on dependence for chips, cloud and model access.",
          before=[MS_F, EXPORT_F],
          after=[F(date="2026-06-03", summary="The Commission's Cloud and AI Development Act proposes sovereignty levels up to 'no third-country control' for cloud serving the public sector (details in the regulation topic).", sources=[CADA])]),
    Topic(id="tech", dimension="technology", title="Open-weight models: Chinese labs and Mistral",
          why_it_matters="Mensch pitched Mistral as Europe's open-weight alternative; where the technical frontier stands decides whether that is viable.",
          before=[F(date="2026", summary="Aggregator sources report Chinese labs holding five of the ten top trending models on Hugging Face and about 41% of downloads over a year; not traced to a primary dataset.", sources=[CN_OPEN])],
          after=[F(date="2026-10-06", summary="Mistral announces Mistral Large 4 ('Le Chonk'), an open-weight model to be released publicly on 27 October 2026. Mensch says it is 'above the Chinese models on certain aspects, including cyber' without naming models or benchmarks. A search summary reports a size of about 1 trillion parameters (49bn active) and an independent index with a Chinese open model at 46 against Mistral's 38: unconfirmed.", sources=[STAR, CYBERNEWS])]),
]
added_m = []
for t in new_m:
    if t.id not in {x.id for x in mensch.topics}:
        mensch.topics.append(t)
        added_m.append(t.id)
if "M9" not in {c.id for c in mensch.claims}:
    mensch.claims.append(Claim(id="M9", speaker="Arthur Mensch", time="00:19:02", kind="forecast", topic="demand",
                               text="If AI takes 10% of Europe's payroll in 3-4 years, that is about €1 trillion, and relying on non-European technology would add a €1 trillion trade deficit.",
                               quote_fr="10% de la masse salariale de l'Europe, c'est à peu près 1 trilliard",
                               checks=[Check(checkpoint="at_meeting", verdict="not_checked", checked_on=TODAY, evidence="Queued: his demand estimate (AI spend as a share of payroll, the size of European payroll, the implied compute) was not checked against analyst forecasts.")],
                               next_step="Compare with analyst forecasts of European AI spending and of power demand from AI (he says about 400 MW for 10% of payroll)."))
mensch.queue += [q for q in [
    "Check Mensch's demand estimates (AI = 10% of payroll; 10% of Europe's payroll about €1 trillion; about 400 MW) against analyst forecasts (M9).",
    "Confirm whether the Cloud and AI Development Act targets a tripling of EU capacity (search summary) or gives no number (law-firm note).",
    "Verify Mistral Large 4's size and benchmark position on an independent leaderboard after its 27 October release.",
] if q not in mensch.queue]
mensch.method += "; context dimensions (demand, finance, regulation, geopolitics_security, technology) added 2026-10-10"

for r in (klaba, mensch):
    d = Path("data/meetings") / r.meeting_uid
    (d / "research.json").write_text(r.model_dump_json(indent=1))
    (d / "research.md").write_text(to_markdown(r))
print("klaba topics added:", added, "| mensch topics added:", added_m)
