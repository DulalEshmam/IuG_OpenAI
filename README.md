# 🏛️ GenAI Museum Project  
**Prototyp zur Generierung von Katalogtexten für Museumsobjekte mittels GenAI (OpenAI API)**  

---

## 👥 Autoren (HTW Berlin)

- Liepa Čivilytė  
- Eshmam Dulal  
- Dawod Ghamudi  
- Milos Schleßing  
- Marceli Kukla  

---

## 🎯 Projektziel

Ziel dieses Projekts ist es, zu untersuchen, **wie generative KI-Modelle** (z. B. GPT-5 oder Gemini) zur **automatischen Erstellung präziser Katalogtexte** in Museen eingesetzt werden können.  
Der Fokus liegt auf der **faktischen Beschreibung** (ohne Interpretation oder Bewertung) von Objekten im Depot des **Technikmuseums Berlin**.

Dieses Projekt ist Teil der Aufgabenstellung:

> *"How can GenAI be used to generate catalogue texts for pictures of objects in the depot of Technikumuseum?"*

---

## ⚙️ Architekturüberblick

Der entwickelte Prototyp besteht aus zwei zentralen Komponenten:

| Komponente | Beschreibung |
|-------------|---------------|
| **`backend.py`** | Enthält die gesamte Logik zur Datenverarbeitung, API-Kommunikation (OpenAI) und den Excel-Export der Ergebnisse. |
| **`gui.py`** | Grafische Benutzeroberfläche auf Basis von **CustomTkinter** mit **Drag & Drop**, Datei-Dialogen und Live-Protokollierung. |

> 💡 Zusätzlich wurde eine alternative Implementierung mit der **Gemini API** entwickelt.  
> 🔗 **Platzhalter-Link:** [Gemini-Prototyp Repository](https://github.com/MilosSchlessing/Informatic-and-Education.git)

---

## 📦 Eingaben & Ausgaben

### 🔹 Eingaben (2 Inputs)
1. **Excel-Datei (.xlsx)**  
   Enthält Metadaten zu Objekten (z. B. Titel, Hersteller, Jahr, Gewicht, Beschreibung).  
   Wichtige Spaltennamen: `T1/T13` für Objekt-ID und Bildpfade.

2. **Bilder-Ordner**  
   Enthält die zugehörigen Objektbilder (JPEG, PNG).  
   Die Zuordnung erfolgt automatisch über **Dateinamen** und **Objekt-IDs**.

> Beide Eingaben werden komfortabel über die **GUI** ausgewählt – wahlweise per **Dateidialog** oder **Drag & Drop**.

### 🔹 Ausgabe
- Eine **Excel-Datei** mit den generierten Katalogtexten in den gewählten Sprachen.  
- Spaltenstruktur:
  - `Object ID`, `Images`
  - `Title_DE`, `Manufacturer_DE`, `Description_DE`, usw. (je Sprache)

---

## 🌍 Sprachunterstützung

Der Prototyp unterstützt aktuell **vier Sprachen**:

| Sprache  | Kürzel | Platzhalter für "nicht angegeben" |
|-----------|--------|----------------------------------|
| Deutsch   | DE     | nicht angegeben                 |
| English   | EN     | not specified                   |
| Polski    | PL     | nie podano                      |
| Lietuvių  | LT     | nenurodyta                      |

Die gewünschte Sprache wird in der GUI über ein Dropdown-Menü ausgewählt.

---

## 🔐 API-Zugriff & `.env`-Datei

Für den Zugriff auf die OpenAI API wird ein **gültiger API Key** benötigt.  
Dieser muss in einer **`.env`-Datei** im Projektverzeichnis hinterlegt werden.

### Beispiel `.env`:
```env
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
```


