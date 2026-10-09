"""Pilot research records for the two hearings (manual research by Claude Code with web search, 2026-10-09).
Provenance: every source below was seen via a web search on 2026-10-09. Where the note says 'page opened' the page itself was read;
where it says 'search summary' only the search-result summary was seen (treat as a lead to confirm)."""
from datetime import date
from pathlib import Path

from parlwatch.research.checkpoints import make_checkpoints
from parlwatch.research.render import to_markdown
from parlwatch.research.schema import Check, Claim, Finding, Research, Source, Topic

TODAY = "2026-10-09"


def S(title, url, tier, note=""):
    return Source(title=title, url=url, tier=tier, accessed=TODAY, note=note)


OPENED = "page opened"
SNIP = "search summary only, page not opened"

# ---- shared sources
AN_PRESS = S("Assemblée nationale: commission d'enquête, phase finale des travaux", "https://www.assemblee-nationale.fr/dyn/espace-presse/communiques-de-presse/2026/commission-d-enquete-dependances-et-vulnerabilites-dans-le-secteur-du-numerique-phase-finale-des-travaux", "primary", OPENED)
LCP_REPORT = S("LCP: le rapport de la commission d'enquête a été adopté", "https://lcp.fr/actualites/numerique-le-rapport-de-la-commission-d-enquete-sur-les-vulnerabilites-de-la-france-a", "secondary", SNIP)
FREEBOX = S("UniversFreebox: un rapport appelle à stopper les nouveaux data centers américains", "https://www.universfreebox.com/article/595903/cloud-un-rapport-appelle-a-stopper-les-nouveaux-data-centers-americains", "secondary", SNIP)
JDE_MORATOIRE = S("Le Journal des Entreprises: un rapport parlementaire demande un moratoire sur les data centers extra-européens", "https://www.lejournaldesentreprises.com/breve/un-rapport-parlementaire-demande-un-moratoire-sur-les-data-centers-extra-europeens-2146626", "secondary", SNIP)
BDT = S("Banque des Territoires: la mission de l'Assemblée appelle l'État à reprendre la main", "https://www.banquedesterritoires.fr/souverainete-numerique-la-mission-de-lassemblee-nationale-appelle-letat-reprendre-la-main", "secondary", SNIP)
COMM_CLOUD = S("European Commission: Commission advances cloud sovereignty through strategic procurement (17 Apr 2026)", "https://commission.europa.eu/news-and-media/news/commission-advances-cloud-sovereignty-through-strategic-procurement-2026-04-17_de", "primary", OPENED)
ORRICK = S("Orrick: Mistral €3B Series D at €21B post-money (Sept 2026)", "https://www.orrick.com/en/News/2026/09/Orrick-Advises-Mistral-in-its-3B-Series-D-at-21B-Post-Money-Valuation", "secondary", OPENED + "; law-firm announcement of the company's own deal")
OMNIBUS_VW = S("VerifyWise: EU AI Act omnibus, what changed on 7 May 2026", "https://verifywise.ai/fr/blog/eu-ai-act-omnibus-what-changed", "weak", OPENED + "; compliance-vendor blog")
OMNIBUS_HUNTON = S("Hunton: EU Digital Omnibus on AI enters into force (Regulation (EU) 2026/1744)", "https://www.hunton.com/privacy-and-cybersecurity-law-blog/eu-digital-omnibus-on-ai-enters-into-force", "secondary", SNIP)
CAMPUS_PR = S("Press release: MGX, Bpifrance, Mistral AI and NVIDIA announce a JV for Europe's largest AI campus", "https://www.polytechnique.edu/sites/default/files/content/communiques/fichiers/2025-05/Communique%20Presse%20-%20MGX%2C%20Bpifrance%2C%20Mistral%20AI%20et%20NVIDIA%20annoncent%20la%20cre%CC%81ation%20d%E2%80%99une%20JV%20pour%20de%CC%81velopper%20en%20France%20le%20plus%20grand%20campus%20IA%20d%27Europe.pdf", "primary", SNIP + "; hosted by Ecole Polytechnique")
CAMPUS_DCD = S("DatacenterDynamics: MGX, Bpifrance, Nvidia and Mistral plan a 1.4 GW campus near Paris", "https://www.datacenterdynamics.com/es/noticias/mgx-bpifrance-nvidia-y-mistral-ai-planean-un-campus-de-centro-de-datos-de-14-gw-en-par%C3%ADs/", "secondary", SNIP)
CAMPUS_FW = S("FrenchWeb: what a new-generation AI campus looks like", "https://www.frenchweb.fr/datacenters-energie-refroidissement-a-quoi-ressemble-un-campus-ia-de-nouvelle-generation/461960", "secondary", SNIP + "; construction expected H2 2026, service 2028, extension to 3 GW")
RTE = S("Connaissance des énergies: 95.2% low-carbon electricity in 2025 (RTE balance)", "https://www.connaissancedesenergies.org/la-production-electrique-bas-carbone-de-la-france-atteint-un-maximum-historique-en-2025", "secondary", SNIP + "; relays RTE's 2025 electricity report: nuclear 373 TWh = 68.1%")
OVH_Q3 = S("Fortuneo/AFP-type wire: OVHcloud accelerates growth in Q3 (FY2026)", "https://bourse.fortuneo.fr/actualites/ovhcloud-acceleration-de-la-croissance-au-troisieme-trimestre-9716469", "secondary", SNIP + "; relays the company's results release of 25 Jun 2026")
OVH_GUID = S("OptionFinance: OVHcloud confirms its annual objectives (25 Jun 2026)", "https://www.optionfinance.fr/info-financiere-en-continu/d/2026-06-25-ovhcloud-porte-par-le-cloud-public-confirme-ses-objectifs-annuels.html", "secondary", SNIP)
OVH_FY25 = S("Fortuneo: OVHcloud passes €1bn annual revenue (FY2025: €1,084.6M, +9.3% organic)", "https://bourse.fortuneo.fr/actualites-amp/ovhcloud-franchit-le-cap-du-milliard-d-euros-de-ca-annuel-5287890", "secondary", SNIP)
OVH_SNC = S("OVHcloud corporate: SNC Cloud Platform obtains SecNumCloud qualification", "https://corporate.ovhcloud.com/en/newsroom/news/ovhcloud-obtains-secnumcloud-qualification-snc-cloud-platform/", "primary", SNIP + "; company press release, 1 Sep 2026")
OVH_WC = S("OVHcloud: 20 years of water cooling", "https://corporate.ovhcloud.com/en/newsroom/news/watercooling-anniversary", "primary", SNIP + "; company says industrial-scale water cooling since 2003, older servers retrofitted by 2004")
OVH_CEO = S("Siècle Digital: Octave Klaba takes the reins again after the CEO's surprise departure (22 Oct 2025)", "https://siecledigital.fr/2025/10/22/ovhcloud-octave-klaba-reprend-la-main-apres-le-depart-surprise-du-directeur-general/", "secondary", SNIP)
CN_OPEN = S("Tech-Insider: DeepSeek and Qwen top Hugging Face in 2026", "https://tech-insider.org/nl/deepseek-qwen-hugging-face-top-2026/", "weak", SNIP + "; aggregator, figures (e.g. '41% of downloads') not traced to a primary dataset")
MISTRAL_ARR = S("Gend: Mistral AI targets €1B revenue in 2026", "https://www.gend.co/blog/mistral-ai-e1b-revenue-2026", "weak", SNIP + "; relays the CEO's 'north of $400M run rate, $1B ARR by end-2026' statement from early 2026")

# =========================================================================== Mensch
mensch = Research(
    meeting_uid="18888392_6a0330a9d4404", title="Hearing of Arthur Mensch (Mistral AI), commission of inquiry on digital dependencies",
    meeting_date="2026-05-12", researched_on=TODAY, checkpoints=make_checkpoints(date(2026, 5, 12)),
    topics=[
        Topic(id="inquiry", title="The commission of inquiry this hearing belongs to",
              why_it_matters="Mensch's answers fed a 45-hearing inquiry whose final report turns the issues he raised (public procurement, preference for European providers, data-centre power) into recommendations.",
              before=[Finding(date="2026-02-03", summary="Commission of inquiry on structural dependencies and systemic vulnerabilities in the digital sector created, chaired by Philippe Latombe (Dem) with Cyrielle Chatelain (ecologist group) as rapporteure. Scope: dependence on non-European infrastructure, cloud, software and AI.", sources=[AN_PRESS])],
              after=[Finding(date="2026-07-08", summary="Report adopted after 45 hearings of 113 people (Mensch among them). Published mid-July: 400+ pages, 18 recommendations and 29 proposals, including an immediate moratorium on new data centres for non-European cloud giants, a European preference in public procurement and funding, open-source solutions reserved for public markets from 2030, and a state veto (golden-share type) against foreign takeover of national champions such as Mistral AI. It found 79% of 2025 spending went to US vendors (81% in 2024).", sources=[AN_PRESS, LCP_REPORT, FREEBOX, BDT])]),
        Topic(id="ai-act", title="EU AI Act and the 'Digital Omnibus' delay",
              why_it_matters="Mensch criticised heavy and fragmented European regulation. The hearing took place days after a provisional deal that postponed the AI Act's high-risk obligations.",
              before=[Finding(date="2026-05-07", summary="Council and Parliament reached a provisional agreement on the Digital Omnibus on AI, five days before the hearing: Annex III high-risk obligations move from 2 Aug 2026 to 2 Dec 2027, Annex I (products) to 2 Aug 2028. General-purpose-AI obligations (in force since Aug 2025) and the Article 5 bans stay.", sources=[OMNIBUS_VW])],
              after=[Finding(date="2026-07-24", summary="Regulation (EU) 2026/1744 (dated 8 Jul 2026) published in the Official Journal on 24 Jul and in force from 27 Jul 2026, confirming the 2027/2028 dates. Open point: sources disagree on whether the Article 50 transparency date also moved (one says to 2 Dec 2026, another says unchanged): check the Official Journal text.", sources=[OMNIBUS_HUNTON, OMNIBUS_VW])]),
        Topic(id="mistral", title="Mistral AI: size, funding and revenue",
              why_it_matters="The figures Mensch gave (valuation, staff, revenue goal, R&D spend) set the baseline for how fast the company's position changes after the hearing.",
              before=[Finding(date="2025-09", summary="Series C of €1.7bn at a €11.7bn valuation. Early 2026: annualised revenue reported 'north of $400M', target about $1bn run rate by end-2026.", sources=[ORRICK, MISTRAL_ARR])],
              after=[Finding(date="2026-04-17", summary="Mistral is named in the Proximus-led group (with S3NS and Clarence) that won one of four lots of the Commission's sovereign cloud contract (up to €180M over 6 years).", sources=[COMM_CLOUD]),
                     Finding(date="2026-09-08", summary="Series D: €3bn at a €21bn post-money valuation, led by Samsung Electronics with Scaleup Europe Fund (EQT) and PSG as co-leads; described as the largest equity round by a European tech company.", sources=[ORRICK])]),
        Topic(id="campus-ia", title="Compute, energy and the 'Campus IA' project",
              why_it_matters="A deputy raised the 1.4 GW Campus IA project in his constituency and compared it with Flamanville; Mensch argued Europe must capture AI value beyond supplying electricity.",
              before=[Finding(date="2025-05", summary="Joint venture of MGX, Bpifrance, Mistral AI and Nvidia announced for a campus at Fouju (Seine-et-Marne): 1.4 GW of colocation, 87 hectares, about €8.5bn reported by Bloomberg, with Bouygues, EDF, RTE among partners. Construction expected from H2 2026, service from 2028, with a later extension to 3 GW on a second site.", sources=[CAMPUS_PR, CAMPUS_DCD, CAMPUS_FW])],
              after=[Finding(date="2026-10", summary="No confirmation of a construction start found yet in the sources searched. This is the main item for the 6-month and 12-month checks.", sources=[])]),
    ],
    claims=[
        Claim(id="M1", speaker="Arthur Mensch", time="00:14:41", kind="figure", topic="mistral",
              text="Mistral has about 1,000 employees and a valuation of €12bn.",
              quote_fr="on est 1000 collaborateurs, une valorisation de 12 milliards d'euros",
              checks=[Check(checkpoint="at_meeting", verdict="supported", checked_on=TODAY, evidence="Last priced round before the hearing was €11.7bn (Sept 2025), consistent with 'about 12'. Headcount not independently checked.", sources=[ORRICK]),
                      Check(checkpoint="3m", verdict="outdated", checked_on=TODAY, evidence="Superseded: the Series D of 8 Sep 2026 values the company at €21bn post-money, about 75-80% above the figure quoted four months earlier.", sources=[ORRICK])],
              next_step="Headcount: check an official source (company announcements, French registry filings) at the 12-month mark."),
        Claim(id="M2", speaker="Arthur Mensch", time="00:14:41", kind="forecast", topic="mistral",
              text="Mistral aims for €1bn of revenue by the end of 2026.",
              quote_fr="1 milliard d'euros de revenus visés d'ici la fin de l'année",
              checks=[Check(checkpoint="at_meeting", verdict="supported", checked_on=TODAY, evidence="Consistent with the CEO's earlier public target (run rate above $400M in Jan 2026, about $1bn ARR by end-2026). It is a target, not a result. The 'revenue' vs 'annualised run rate' wording is ambiguous.", sources=[MISTRAL_ARR]),
                      Check(checkpoint="3m", verdict="pending", checked_on=TODAY, evidence="No updated revenue figure found; the Series D announcement gives none. Outcome knowable from Dec 2026 to Q1 2027.", sources=[ORRICK])],
              next_step="Re-check at 6m (Nov 2026) and 12m: look for any ARR announcement and whether it is run rate or recognised revenue."),
        Claim(id="M3", speaker="Arthur Mensch", time="00:13:38", kind="figure", topic="mistral",
              text="Mistral has invested a billion (euros) in R&D this year.", quote_fr="on a investi un milliard cette année dans les sujets de R&D",
              checks=[Check(checkpoint="3m", verdict="unverifiable", checked_on=TODAY, evidence="No independent figure found. Funding raised (€1.7bn Sept 2025, €3bn Sept 2026) makes it plausible, but plausibility is not evidence.")],
              next_step="Low priority; look for audited accounts if the company files them."),
        Claim(id="M4", speaker="Arthur Mensch", time="01:09:24", kind="figure", topic="mistral",
              text="Public procurement is about 20% of Mistral's revenue, 10% of it French.", quote_fr="C'est 20% dont 10% de la commande publique française",
              checks=[Check(checkpoint="3m", verdict="unverifiable", checked_on=TODAY, evidence="Company-sourced and answered off the cuff in the hearing ('15%... a bit more, 20%'). No public breakdown found. Context: Mistral sits in one of the four lots of the EU sovereign-cloud contract.", sources=[COMM_CLOUD])],
              next_step="Look for ministry or parliamentary figures on Mistral public contracts."),
        Claim(id="M5", speaker="Arthur Mensch", time="00:31:31", kind="opinion", topic="campus-ia",
              text="If Europe's only role is supplying energy for AI, about 90% of the value is elsewhere.", quote_fr="si le seul rôle de l'Europe, c'est d'être le fournisseur d'énergie, ça veut dire qu'il y a 90% de la valeur qui est ailleurs",
              checks=[Check(checkpoint="3m", verdict="unverifiable", checked_on=TODAY, evidence="An estimate from his own value-chain split (roughly 10% of the value of a token goes to the electricity). Not a published figure; treat as an argument, not data.")],
              next_step="Find an independent breakdown of AI value-chain economics (analyst or academic) to compare."),
        Claim(id="M6", speaker="Arthur Mensch", time="00:50:00", kind="figure", topic="campus-ia",
              text="About 70% of French electricity is nuclear.", quote_fr="les électrons, 70% c'est nucléaire",
              checks=[Check(checkpoint="3m", verdict="supported", checked_on=TODAY, evidence="RTE's 2025 balance puts nuclear at 373 TWh, 68.1% of French electricity: '70%' is a fair rounding.", sources=[RTE])]),
        Claim(id="M7", speaker="Arthur Mensch", time="00:21:38", kind="policy_position", topic="ai-act",
              text="Europe's regulation is heavier than elsewhere and its market is fragmented (though he also sees fragmentation as an asset: longer-term partnerships). Later he adds that rules pile up incoherently, force heavy documentation, and require a new legal entity in each country.",
              quote_fr="on a une réglementation qui est plus lourde, on a un marché qui est fragmenté",
              checks=[Check(checkpoint="3m", verdict="pending", checked_on=TODAY, evidence="A position, not true/false. Developments since: the EU postponed the AI Act's high-risk obligations (Regulation 2026/1744, in force 27 Jul 2026) and the inquiry report asks for a 'secure and simplified' legal framework. Not addressed: the general-purpose-AI obligations that apply to model builders like Mistral, and the need for a legal entity per country. He did not name the AI Act in the passages found.", sources=[OMNIBUS_HUNTON, BDT])],
              next_step="Track the Commission's announced sovereignty package and any single-market measures for AI providers. Elaboration in the hearing: 00:55:31-00:56:43."),
        Claim(id="M8", speaker="Deputy (Campus IA question)", time="00:42:01", kind="fact", topic="campus-ia",
              text="A 'Campus IA' mega-project is being set up north of the deputy's constituency, about 1.4-1.6 GW, comparable to Flamanville.", quote_fr="il y a un méga projet qui est en train de s'installer qui s'appelle Campus IA",
              checks=[Check(checkpoint="at_meeting", verdict="supported", checked_on=TODAY, evidence="Campus IA at Fouju is a 1.4 GW project announced in May 2025; Flamanville 3 is a 1.6 GW reactor. Note it is planned, not yet built (construction expected from H2 2026).", sources=[CAMPUS_PR, CAMPUS_FW])],
              next_step="6m/12m: has construction started? Is the 3 GW extension site named?"),
    ],
    queue=["Check headcount and R&D figures in any filed accounts.", "Read the inquiry report's chapter on AI to see which of Mensch's statements it cites.",
           "Confirm Article 50 transparency date in the Official Journal text of Regulation (EU) 2026/1744.", "Open the report PDF itself (only press summaries were read)."])
mensch.checkpoints[0].done_on = TODAY
mensch.checkpoints[0].note = "evaluated in retrospect"
mensch.checkpoints[1].done_on = TODAY
mensch.checkpoints[1].note = "done 58 days after the due date: covers events up to 2026-10-09 (about 5 months)"

# =========================================================================== Klaba
klaba = Research(
    meeting_uid="19471620_6abccf18f0e48", title="Hearing of Octave Klaba (OVHcloud), Economic Affairs Committee",
    meeting_date="2026-09-30", researched_on=TODAY, checkpoints=make_checkpoints(date(2026, 9, 30)),
    topics=[
        Topic(id="inquiry", title="The inquiry report that frames this hearing",
              why_it_matters="Klaba had already testified on 21 April 2026 to the commission of inquiry, whose report appeared two and a half months before this hearing; deputies quote it.",
              before=[Finding(date="2026-04-21", summary="Klaba's earlier hearing before the commission of inquiry (the chair recalls his statement that European public procurement was far too small to build champions).", sources=[AN_PRESS]),
                      Finding(date="2026-07-15", summary="Inquiry report published: moratorium on new data centres for non-European hyperscalers, European preference in procurement. It computes that of about 15 GW of data-centre capacity expected in roughly five years, only 1.4 GW would go to European operators.", sources=[JDE_MORATOIRE, FREEBOX, AN_PRESS])],
              after=[]),
        Topic(id="eu-cloud", title="The Commission's €180M sovereign cloud contract",
              why_it_matters="Klaba used it as an example: a start for European providers, but small next to hyperscaler revenue.",
              before=[Finding(date="2025-10", summary="Tender launched under a new Cloud Sovereignty Framework (eight sovereignty objectives, SEAL levels).", sources=[COMM_CLOUD]),
                      Finding(date="2026-04-17", summary="Awarded: up to €180M over 6 years, four contracts: Post Telecom (lead) with OVHcloud and Clever Cloud; STACKIT (Schwarz Group); Scaleway (Iliad); Proximus (lead) with S3NS, Clarence and Mistral. Winners needed at least SEAL-2.", sources=[COMM_CLOUD])],
              after=[]),
        Topic(id="ovh", title="OVHcloud: results, leadership and qualifications",
              why_it_matters="Revenue and qualification claims made at the hearing can be compared with official results as they are published.",
              before=[Finding(date="2025-10-20", summary="Octave Klaba returns as chairman and CEO after the CEO's departure.", sources=[OVH_CEO]),
                      Finding(date="2025-12", summary="FY2025 revenue €1,084.6M (+9.3% organic), adjusted EBITDA €437.8M (40.4%).", sources=[OVH_FY25]),
                      Finding(date="2026-06-25", summary="Q3 FY2026 revenue €289.6M (+6.9% like-for-like), public cloud +20.2%. FY2026 guidance confirmed: organic growth 5-7%, adjusted EBITDA margin above 2025.", sources=[OVH_Q3, OVH_GUID]),
                      Finding(date="2026-09-01", summary="SNC Cloud Platform obtains SecNumCloud qualification from ANSSI, OVHcloud's third (after Bare Metal Pod and VMware on OVHcloud). A decree of 14 Apr 2026 requires certified cloud for sensitive State data.", sources=[OVH_SNC])],
              after=[Finding(date="2026-10", summary="FY2026 results (year ending 31 Aug) are due after the hearing; the date was not found in the sources searched.", sources=[])]),
        Topic(id="compute", title="Data-centre scale, energy and AI infrastructure in France",
              why_it_matters="Klaba said a single-site gigawatt data centre will never exist in Europe; a 1.4 GW campus is planned in France.",
              before=[Finding(date="2025-05", summary="Campus IA at Fouju announced: 1.4 GW, service from 2028, construction expected from H2 2026.", sources=[CAMPUS_PR, CAMPUS_FW])],
              after=[]),
        Topic(id="china-open", title="Dependence on Chinese open-weight AI models",
              why_it_matters="Klaba argued Europe's AI depends on Chinese open source, a strategic risk.",
              before=[Finding(date="2026", summary="Aggregator sources report Chinese labs holding five of the ten top trending models on Hugging Face and about 41% of downloads over a year. Not traced to a primary dataset.", sources=[CN_OPEN])],
              after=[]),
    ],
    claims=[
        Claim(id="K1", speaker="Octave Klaba", time="00:17:25", kind="figure", topic="eu-cloud",
              text="The €180M contract amounts to about €40M a year shared among 4 winners.", quote_fr="ces 180 millions qui, globalement, vont représenter environ 40 millions par an sur 4 gagnants",
              checks=[Check(checkpoint="at_meeting", verdict="partly_supported", checked_on=TODAY, evidence="The Commission awarded 'up to €180M over 6 years' = at most €30M a year, not €40M (his figure implies a term of about 4.5 years). The ceiling is also not committed spend. His point (small next to hyperscaler spend) is unaffected.", sources=[COMM_CLOUD])],
              next_step="3m/12m: look for call-off volumes actually placed under the contract."),
        Claim(id="K2", speaker="Octave Klaba", time="00:17:38", kind="figure", topic="eu-cloud",
              text="AWS earns about €1.2bn a year from the European Commission and Azure about €500M.", quote_fr="environ 1,2 milliard de chiffre d'affaires que AWS réalise avec la Commission européenne par an. Et vous avez un autre 500 millions chez Azure",
              checks=[Check(checkpoint="at_meeting", verdict="unverifiable", checked_on=TODAY, evidence="No public itemised figure found; the Commission has relied on framework contracts with the US hyperscalers but amounts per vendor were not found. Possibly an estimate covering all EU bodies.")],
              next_step="Search the EU Financial Transparency System, TED award notices and parliamentary questions."),
        Claim(id="K3", speaker="Octave Klaba", time="00:32:53", kind="figure", topic="ovh",
              text="OVHcloud makes €1.2bn in revenue and is on the slope towards €2bn.", quote_fr="OVH fait 1,2 milliard et on est sur la pente de 2 milliards de chiffres d'affaires",
              checks=[Check(checkpoint="at_meeting", verdict="partly_supported", checked_on=TODAY, evidence="Reported FY2025 revenue is €1,085M; with 5-7% organic growth guided for FY2026 (year to 31 Aug 2026) revenue would be about €1.14-1.16bn before currency effects (my calculation), so '1.2' rounds up. The €2bn is an ambition with no date; he declined to give dates, citing listed-company rules.", sources=[OVH_FY25, OVH_GUID, OVH_Q3])],
              next_step="3m: compare with the FY2026 results (due after the hearing). Revisit '2bn' only if a date is given."),
        Claim(id="K4", speaker="Stéphane Travert (chair)", time="00:06:21", kind="fact", topic="ovh",
              text="OVHcloud obtained SecNumCloud 3.2 qualification on 1 September for its SNC Cloud Platform.", quote_fr="votre groupe a obtenu, le 1er septembre dernier, la qualification Secnum Cloud 3.2",
              checks=[Check(checkpoint="at_meeting", verdict="supported", checked_on=TODAY, evidence="OVHcloud announced the qualification on 1 Sep 2026; it is the company's third SecNumCloud qualification.", sources=[OVH_SNC])]),
        Claim(id="K5", speaker="Octave Klaba", time="00:25:01", kind="forecast", topic="compute",
              text="A single address with a gigawatt of electrical power for data centres will never exist in Europe or in France.", quote_fr="les lieux où il y aura un gigawatt de puissance électrique déployée dans un data center, une adresse, pour moi, ça ne va jamais exister en Europe et en France",
              checks=[Check(checkpoint="at_meeting", verdict="pending", checked_on=TODAY, evidence="In tension with announced plans: Campus IA at Fouju is a 1.4 GW campus (service from 2028, 87 ha, a dozen buildings). A 'never' forecast cannot be proven wrong yet; what can be tracked is whether construction starts and permits are granted.", sources=[CAMPUS_PR, CAMPUS_FW])],
              next_step="6m: construction started in H2 2026? 12m: phase-1 delivery schedule and grid connection."),
        Claim(id="K6", speaker="A deputy (not identified)", time="01:05:02", kind="figure", topic="inquiry",
              text="Of 15 GW of secured data-centre capacity in France, only 1.4 GW will benefit exclusively European operators, per the inquiry report.", quote_fr="Sur 15 gigawatts de capacité sécurisée en France, seuls 1,4 ne profiteront qu'aux opérateurs européens",
              checks=[Check(checkpoint="at_meeting", verdict="supported", checked_on=TODAY, evidence="Press coverage of the report repeats these figures (15 GW, 1.4 GW for European players). The report PDF itself was not opened.", sources=[JDE_MORATOIRE, FREEBOX])],
              next_step="Open the report and read how the 15 GW and 1.4 GW are defined."),
        Claim(id="K7", speaker="Octave Klaba", time="00:37:56", kind="fact", topic="china-open",
              text="Europe relies heavily on open-source AI that is Chinese; innovations come mostly from China.", quote_fr="on fait beaucoup de confiance à l'open source, à juste titre, parce qu'il est bon, mais il est chinois",
              checks=[Check(checkpoint="at_meeting", verdict="partly_supported", checked_on=TODAY, evidence="Direction plausible: reports say Chinese open-weight models dominate download and trending rankings. But only weak aggregator sources were found, no European-specific figures, and Mistral's open-weight models are a counter-example.", sources=[CN_OPEN])],
              next_step="Find primary data (Hugging Face, OpenRouter usage, academic studies) and any figure for European adoption."),
        Claim(id="K8", speaker="Octave Klaba", time="00:43:26", kind="fact", topic="ovh",
              text="OVHcloud has cooled its data centres with water since 2004.", quote_fr="depuis 2004, nous refroidissons les data centres avec de l'eau",
              checks=[Check(checkpoint="at_meeting", verdict="supported", checked_on=TODAY, evidence="OVHcloud dates industrial-scale water cooling to 2003, with older servers retrofitted by 2004.", sources=[OVH_WC])]),
        Claim(id="K9", speaker="Octave Klaba", time="00:26:59", kind="policy_position", topic="eu-cloud",
              text="Redirecting 5-15% of public digital procurement to European providers would create European giants.", quote_fr="Si vous mettez 5, 10 ou 15 %, vous allez créer des géants en Europe",
              checks=[Check(checkpoint="at_meeting", verdict="pending", checked_on=TODAY, evidence="A position, not a fact. Related decisions: the inquiry recommends a European preference in procurement; the EU awarded its sovereign cloud contract to European providers; no binding percentage found.", sources=[AN_PRESS, COMM_CLOUD])],
              next_step="Track the Commission's sovereignty package and any French procurement rule changes."),
    ],
    queue=["Open the inquiry report and check how it uses Klaba's 21 April testimony.", "Find the FY2026 results date.",
           "Check Klaba's claims about the 'no multi-gigawatt site' reasoning (permits, grid) against RTE/government statements."])
klaba.checkpoints[0].done_on = TODAY
klaba.checkpoints[0].note = "evaluated 9 days after the hearing"

for r in (mensch, klaba):
    d = Path("data/meetings") / r.meeting_uid
    (d / "research.json").write_text(r.model_dump_json(indent=1))
    (d / "research.md").write_text(to_markdown(r))
    print(r.meeting_uid, len(r.topics), "topics,", len(r.claims), "claims,", sum(len(c.checks) for c in r.claims), "checks")
