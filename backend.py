import os
import re
import base64
import time
import pandas as pd
import requests
from dotenv import load_dotenv
from dataclasses import dataclass
import queue

# ==============================
# Konfiguration & Hilfsfunktionen
# ==============================
@dataclass
class ProcessingConfig:
    input_path: str         # Pfad zum Bilder-Ordner
    csv_path: str           # Pfad zur Excel-Datei
    output_path: str        # Zielpfad für Ergebnis-Excel
    languages: list         # Liste der Sprach-Namen

def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise ValueError("❌ No OPENAI_API_KEY found! Please check your .env")

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
MODEL = "gpt-5"  # Vision-fähig

LANG_SETTINGS = {
    "Deutsch":  {"suffix": "DE", "ns": "nicht angegeben"},
    "English":  {"suffix": "EN", "ns": "not specified"},
    "Polski":   {"suffix": "PL", "ns": "nie podano"},
    "Lietuvių": {"suffix": "LT", "ns": "nenurodyta"},
}

BASE_PROMPT = (
    "You are a registrar / documentation specialist in a technical museum. "
    "Create a factual, verifiable catalog entry. "
    "Describe only characteristics explicitly stated in the metadata or clearly visible/identified: "
    "form, materials, construction/components, visible surface features, inscriptions/markings, dimensions/weight, condition traces. "
    "Do not provide interpretations, assumptions, historical context, or inferred functions. "
    "Do not mention functions or uses unless explicitly stated. "
    "Avoid subjective adjectives and speculative language. "
    "Write in precise, neutral museum terminology. "
    "Use only the provided information."
)

OUTPUT_SCHEMA = (
    "Provide the entry in the following exact label format. "
    "Write the content in {language_name} (the labels remain in English):\n"
    "Title: <text or '{ns}'>\n"
    "Object ID: <value>\n"
    "Manufacturer/Collection: <value or '{ns}'>\n"
    "Date: <value or '{ns}'>\n"
    "Dimensions: <value or '{ns}'>\n"
    "Weight: <value or '{ns}'>\n"
    "Location: <value or '{ns}'>\n"
    "Description: 2–5 sentences. Only observable/stated features. No function, context, or evaluation."
)

# ==============================
# OpenAI-Call
# ==============================
def generate_catalog_text(image_paths, prompt_text):
    image_contents = []
    for p in image_paths:
        b64 = encode_image(p)
        image_contents.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
        })

    payload = {
        "model": MODEL,
        "messages": [{
            "role": "user",
            "content": [{"type": "text", "text": prompt_text}, *image_contents]
        }]
    }
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

    for attempt in range(3):
        try:
            resp = requests.post(OPENAI_URL, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except requests.exceptions.RequestException as e:
            if hasattr(e, "response") and e.response is not None:
                txt = e.response.text
                if "rate_limit_exceeded" in txt or e.response.status_code == 429:
                    wait = 10 * (attempt + 1)
                    time.sleep(wait)
                    continue
            return f"❌ API Error: {str(e)}"
    return "❌ Failed after retries."

# ==============================
# Parsing
# ==============================
KNOWN_LABELS = [
    "Title", "Object ID", "Manufacturer/Collection", "Date",
    "Dimensions", "Weight", "Location", "Description"
]
LABEL_RE = re.compile(r"^\s*(" + "|".join(re.escape(l) for l in KNOWN_LABELS) + r")\s*:\s*(.*)$", re.IGNORECASE)

def parse_structured(text: str):
    result = {k: "" for k in KNOWN_LABELS}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        m = LABEL_RE.match(lines[i])
        if m:
            label = m.group(1)
            value = m.group(2).strip()
            if label.lower() == "description":
                desc_lines = [value] if value else []
                i += 1
                while i < len(lines) and not LABEL_RE.match(lines[i]):
                    if lines[i].strip():
                        desc_lines.append(lines[i].strip())
                    i += 1
                result["Description"] = " ".join(desc_lines).strip()
                continue
            else:
                result[label] = value
        i += 1
    return result

# ==============================
# Hauptverarbeitung
# ==============================
def run_processing_logic(config: ProcessingConfig, log_queue: queue.Queue = None):
    def log(msg):
        if log_queue:
            log_queue.put(msg)
        else:
            print(msg)

    log(f"📁 Lade Datei: {config.csv_path}")
    df = pd.read_excel(config.csv_path)

    id_col = next((c for c in ["T1", "t1"]  if c in df.columns), None)
    img_col = next((c for c in ["T13", "t13"] if c in df.columns), None)
    if not id_col or not img_col:
        log("❌ Spalten T1/t1 und T13/t13 nicht gefunden.")
        return

    ctx_map = {
        "title":       ["T3", "t3"],
        "manufacturer":["T2", "t2"],
        "desc":        ["T5", "t5"],
        "date":        ["T14", "t14"],
        "weight":      ["T6", "t6"],
        "location":    ["T8", "t8"],
        "notes":       ["T7", "t7"],
    }

    grouped = df.groupby(id_col)
    results_rows = []

    base_cols = ["Object ID", "Images"]
    lang_cols = []
    for lang in config.languages:
        suf = LANG_SETTINGS[lang]["suffix"]
        lang_cols += [
            f"Title_{suf}",
            f"Manufacturer_{suf}",
            f"Date_{suf}",
            f"Dimensions_{suf}",
            f"Weight_{suf}",
            f"Location_{suf}",
            f"Description_{suf}",
        ]
    all_cols = base_cols + lang_cols

    log(f"🌍 Sprachen: {', '.join(config.languages)}")
    log(f"🔢 Objekte: {len(grouped)}\n")

    for object_id, group in grouped:
        object_id = str(object_id).strip()
        if not object_id:
            continue
        log(f"🔍 Objekt: {object_id}")

        image_paths = []
        for field in group[img_col].dropna().astype(str).tolist():
            clean = field.replace("\\\\", "\\").replace("\r", "").strip()
            for line in clean.splitlines():
                filename = os.path.basename(line.replace("\\", "/")).strip()
                if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
                    continue
                year = next((p for p in object_id.split("/") if p.isdigit() and len(p) == 4), None)
                full_path = os.path.join(config.input_path, year, filename) if year else os.path.join(config.input_path, filename)
                if os.path.exists(full_path):
                    image_paths.append(full_path)
                else:
                    log(f"⚠️ Bild fehlt: {full_path}")

        if not image_paths:
            log("⚠️ Keine gültigen Bilder → überspringe\n")
            row = {"Object ID": object_id, "Images": ""}
            for lang in config.languages:
                suf = LANG_SETTINGS[lang]["suffix"]
                row.update({
                    f"Title_{suf}": "",
                    f"Manufacturer_{suf}": "",
                    f"Date_{suf}": "",
                    f"Dimensions_{suf}": "",
                    f"Weight_{suf}": "",
                    f"Location_{suf}": "",
                    f"Description_{suf}": "❌ No valid image found",
                })
            results_rows.append(row)
            continue

        first = group.iloc[0]
        def pick(cols): return next((first[c] for c in cols if c in df.columns and pd.notna(first[c])), "")

        ctx_title        = pick(ctx_map["title"])
        ctx_manufacturer = pick(ctx_map["manufacturer"])
        ctx_desc         = pick(ctx_map["desc"])
        ctx_date         = pick(ctx_map["date"])
        ctx_weight       = pick(ctx_map["weight"])
        ctx_location     = pick(ctx_map["location"])
        ctx_notes        = pick(ctx_map["notes"])

        row = {"Object ID": object_id, "Images": ", ".join(os.path.basename(p) for p in image_paths)}

        for lang in config.languages:
            ns  = LANG_SETTINGS[lang]["ns"]
            suf = LANG_SETTINGS[lang]["suffix"]

            title_p   = ctx_title if str(ctx_title).strip() else ns
            manuf_p   = ctx_manufacturer if str(ctx_manufacturer).strip() else ns
            date_p    = ctx_date if str(ctx_date).strip() else ns
            dim_p     = ctx_desc if str(ctx_desc).strip() else ns
            weight_p  = ctx_weight if str(ctx_weight).strip() else ns
            loc_p     = ctx_location if str(ctx_location).strip() else ns
            notes_p   = ctx_notes if str(ctx_notes).strip() else ns

            metadata_context = (
                f"Object ID: {object_id}\n"
                f"Title: {title_p}\n"
                f"Manufacturer/Collection: {manuf_p}\n"
                f"Date: {date_p}\n"
                f"Dimensions/Description: {dim_p}\n"
                f"Weight: {weight_p}\n"
                f"Location: {loc_p}\n"
                f"Additional Notes: {notes_p}\n"
            )
            prompt = (
                f"{BASE_PROMPT}\n\n"
                f"Write the content in {lang}.\n\n"
                f"{metadata_context}\n\n"
                f"{OUTPUT_SCHEMA.format(language_name=lang, ns=ns)}"
            )

            text = generate_catalog_text(image_paths, prompt)
            parsed = parse_structured(text)

            row.update({
                f"Title_{suf}":        parsed.get("Title", ""),
                f"Manufacturer_{suf}": parsed.get("Manufacturer/Collection", ""),
                f"Date_{suf}":         parsed.get("Date", ""),
                f"Dimensions_{suf}":   parsed.get("Dimensions", ""),
                f"Weight_{suf}":       parsed.get("Weight", ""),
                f"Location_{suf}":     parsed.get("Location", ""),
                f"Description_{suf}":  parsed.get("Description", ""),
            })

            log(f"   ✅ {lang} erledigt")
            time.sleep(1.5)

        results_rows.append(row)
        log("")

    df_out = pd.DataFrame(results_rows, columns=all_cols)
    df_out.to_excel(config.output_path, index=False)
    log(f"\n📘 Gespeichert unter: {config.output_path}")
    if log_queue:
        log_queue.put("FINISHED")
