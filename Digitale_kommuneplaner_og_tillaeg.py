# Generated from: Digitale_kommuneplaner_og_tillaeg.ipynb
# Converted at: 2026-08-07T09:25:47.445Z
# Next step (optional): refactor into modules & generate tests with RunCell
# Quick start: pip install runcell

import requests
import pandas as pd
import time
from datetime import datetime

# --------------------------------------------------
# Hent kommuneliste
# --------------------------------------------------

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/138.0 Safari/537.36"
    )
}

response = requests.get(
    "https://kommuneplaner.plandata.dk/assets/kommuner.json",
    headers=headers,
    timeout=60
)

print("STATUS:", response.status_code)

print("HEADERS:")
print(response.headers)

print("FIRST 1000 CHARS:")
print(response.text[:1000])

response.raise_for_status()

kommuner = response.json()

response.raise_for_status()

try:
    kommuner = response.json()
except Exception:
    print("Kunne ikke læse kommunelisten.")
    print(response.text[:500])
    raise

kommuneplan_resultater = []
tillaeg_resultater = []

# --------------------------------------------------
# Gennemgå kommuner
# --------------------------------------------------

for kommune in kommuner:

    kode = kommune["kode"]
    navn = kommune.get("kommuneNavn", kommune["navn"])

    print(f"Behandler {navn}")

    try:

        # ------------------------------------------
        # Hent nyeste vedtagne kommuneplan
        # ------------------------------------------

        kp_url = (
            "https://indberet.plandata.dk/plandata-api/offentlig/"
            "hentOffentligePlaner"
            f"?kommunekode={kode}"
            "&plantype=KOMMUNEPLAN"
            "&planstatus=VEDTAGET"
            "&orderBy=datoikraft%20DESC"
        )

        kp_data = requests.get(
            kp_url,
            headers=headers,
            timeout=30
        ).json()

        planer = kp_data.get("data", [])

        if len(planer) == 0:

            kommuneplan_resultater.append({
                "Kommunenavn": navn,
                "Kommunekode": kode,
                "Digital?": "Ingen plan"
            })

            continue

        aktuel_plan = planer[0]

        aktuel_plan_id = aktuel_plan["planId"]

        kommuneplan_digital = (
            "Ja"
            if aktuel_plan.get("erDigital", False)
            else "Nej"
        )

        kommuneplan_resultater.append({
            "Kommunenavn": navn,
            "Kommunekode": kode,
            "Digital?": kommuneplan_digital
        })

        # ------------------------------------------
        # Hent kommuneplantillæg
        # ------------------------------------------

        tillaeg_url = (
            "https://indberet.plandata.dk/plandata-api/offentlig/"
            "hentOffentligePlaner"
            f"?kommunekode={kode}"
            "&plantype=KOMMUNEPLANTILLAEG"
            "&maxPageSize=10000"
        )

        tillaeg_data = requests.get(
            tillaeg_url,
            headers=headers,
            timeout=30
        ).json()

        for plan in tillaeg_data.get("data", []):

            # Ignorer aflyste tillæg
            if plan.get("aflysningsdato") is not None:
                continue

            # Kun tillæg til aktuel kommuneplan
            if plan.get("kommuneplanId") != aktuel_plan_id:
                continue

            tillaeg_resultater.append({
                "Kommunenavn": navn,
                "Kommunekode": kode,
                "Tillægsnavn": plan.get("plannavn"),
                "PlanID": plan.get("planId"),
                "Digital?": (
                    "Ja"
                    if plan.get("erDigital", False)
                    else "Nej"
                )
            })

        time.sleep(0.05)

    except Exception as e:

        print(f"Fejl for {navn}: {e}")

        kommuneplan_resultater.append({
            "Kommunenavn": navn,
            "Kommunekode": kode,
            "Digital?": "Fejl"
        })

# --------------------------------------------------
# DataFrames
# --------------------------------------------------

df_planer = pd.DataFrame(kommuneplan_resultater)
df_tillaeg = pd.DataFrame(tillaeg_resultater)

df_planer = df_planer.sort_values("Kommunenavn")

if not df_tillaeg.empty:
    df_tillaeg = df_tillaeg.sort_values(
        ["Kommunenavn", "Tillægsnavn"]
    )

# --------------------------------------------------
# Gem CSV-filer
# --------------------------------------------------

df_planer.to_csv(
    "kommuneplaner_digital_status.csv",
    index=False,
    encoding="utf-8-sig"
)

df_tillaeg.to_csv(
    "kommuneplantillaeg_aktuelle.csv",
    index=False,
    encoding="utf-8-sig"
)

# --------------------------------------------------
# Statistik kommuneplaner
# --------------------------------------------------

digitale_kommuner = sorted(
    df_planer[
        df_planer["Digital?"] == "Ja"
    ]["Kommunenavn"].tolist()
)

antal_digitale_planer = len(digitale_kommuner)

antal_planer = len(
    df_planer[
        df_planer["Digital?"].isin(["Ja", "Nej"])
    ]
)

# --------------------------------------------------
# Statistik tillæg
# --------------------------------------------------

digitale_tillaeg = df_tillaeg[
    df_tillaeg["Digital?"] == "Ja"
]

antal_digitale_tillaeg = len(digitale_tillaeg)
antal_tillaeg = len(df_tillaeg)

digitale_pr_kommune = (
    digitale_tillaeg
    .groupby("Kommunenavn")
    .size()
)

samlede_pr_kommune = (
    df_tillaeg
    .groupby("Kommunenavn")
    .size()
)

kommuner_tillaeg = []

for kommune in samlede_pr_kommune.index:

    digitale = int(
        digitale_pr_kommune.get(kommune, 0)
    )

    samlede = int(
        samlede_pr_kommune.get(kommune, 0)
    )

    kommuner_tillaeg.append(
        (kommune, digitale, samlede)
    )

kommuner_tillaeg.sort(
    key=lambda x: x[1],
    reverse=True
)

# --------------------------------------------------
# HTML-lister
# --------------------------------------------------

venstre_liste = "\n".join(
    f"<li>{kommune}</li>"
    for kommune in digitale_kommuner
)

hoejre_liste = "\n".join(
    f"<li>{kommune} ({digitale} af {samlede})</li>"
    for kommune, digitale, samlede in kommuner_tillaeg
)

# --------------------------------------------------
# HTML
# --------------------------------------------------

opdateret = datetime.now().strftime(
    "%d-%m-%Y %H:%M"
)

html = f"""
<!DOCTYPE html>
<html lang="da">

<head>

<meta charset="UTF-8">

<title>Digitalisering af Kommuneplaner</title>

<meta name="viewport" content="width=device-width, initial-scale=1">

<style>

body {{
    margin: 0;
    background: #f4f7f5;
    font-family: "Segoe UI", Arial, sans-serif;
    color: #1f2937;
}}

.header {{
    background: #0f4c3a;
    color: white;
    padding: 32px;
}}

.header-inner {{
    max-width: 1200px;
    margin: auto;
}}

.header h1 {{
    margin: 0;
}}

.wrapper {{
    max-width: 1200px;
    margin: auto;
    padding: 30px;
}}

.intro {{
    background: white;
    padding: 25px;
    border-radius: 12px;
    margin-bottom: 25px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.06);
}}

.stat-grid {{
    display: flex;
    gap: 20px;
    margin-bottom: 30px;
}}

.stat-card {{
    flex: 1;
    background: white;
    border-radius: 12px;
    padding: 25px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.08);
}}

.stat-number {{
    font-size: 42px;
    font-weight: 700;
    color: #0f4c3a;
}}

.container {{
    display: flex;
    gap: 24px;
}}

.column {{
    flex: 1;
    background: white;
    border-radius: 12px;
    padding: 25px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.08);
}}

.column h2 {{
    margin-top: 0;
    color: #0f4c3a;
    border-bottom: 2px solid #e5e7eb;
    padding-bottom: 12px;
}}

ul {{
    padding-left: 20px;
}}

li {{
    margin-bottom: 8px;
}}

.footer {{
    text-align: center;
    color: #666;
    margin-top: 40px;
    padding-bottom: 30px;
}}

a {{
    color: #0f4c3a;
}}

@media(max-width:900px) {{

    .container {{
        flex-direction: column;
    }}

    .stat-grid {{
        flex-direction: column;
    }}

}}

</style>

</head>

<body>

<div class="header">

    <div class="header-inner">

        <h1>Digitalisering af Kommuneplaner i Danmark</h1>

    </div>

</div>

<div class="wrapper">

    <div class="intro">

        <h2>Status for digitalisering</h2>

        <p>
        Denne side viser status for digitale kommuneplaner og
        digitale kommuneplantillæg i Danmark.
        </p>

        <p>
        Data hentes automatisk fra Plandata.dk og opdateres,
        hver gang scriptet køres.
        </p>

    </div>

    <div class="stat-grid">

        <div class="stat-card">

            <h3>Digitale kommuneplaner</h3>

            <div class="stat-number">
                {antal_digitale_planer}
            </div>

            <p>
                ud af {antal_planer} kommuneplaner
            </p>

        </div>

        <div class="stat-card">

            <h3>Digitale kommuneplantillæg</h3>

            <div class="stat-number">
                {antal_digitale_tillaeg}
            </div>

            <p>
                ud af {antal_tillaeg} tillæg
            </p>

        </div>

    </div>

    <div class="container">

        <div class="column">

            <h2>Kommuner med digital kommuneplan</h2>

            <ul>
                {venstre_liste}
            </ul>

        </div>

        <div class="column">

            <h2>Digitale kommuneplantillæg pr. kommune</h2>

            <ul>
                {hoejre_liste}
            </ul>

        </div>

    </div>

    <div class="footer">

        Senest opdateret: {opdateret}

    </div>

</div>

</body>
</html>
"""

with open(
    "index.html",
    "w",
    encoding="utf-8"
) as f:
    f.write(html)

print()
print("Færdig.")
print("CSV-filer opdateret.")
print("HTML-side gemt som index.html")
