import os
import threading
import queue
import customtkinter as ctk
from tkinter import filedialog
from tkinterdnd2 import TkinterDnD, DND_FILES

# Importiere deine Logik aus backend
from backend import ProcessingConfig, run_processing_logic

# ==============================
# GUI-Anwendung
# ==============================
class App(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.TkdndVersion = TkinterDnD._require(self)

        self.title("Museum Object Description Generator")
        self.geometry("800x700")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.log_queue = queue.Queue()
        self.processing_thread = None

        self.create_widgets()
        self.update_log_widget()

    def create_widgets(self):
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(padx=20, pady=20, fill="both", expand=True)

        # Eingabe: Bilder-Ordner
        ctk.CTkLabel(main_frame, text="1. Bilder-Ordner", font=("Arial", 14, "bold")).pack(anchor="w", padx=10)
        self.folder_path_entry = ctk.CTkEntry(main_frame, placeholder_text="Ordner hierher ziehen oder auf 'Durchsuchen' klicken")
        self.folder_path_entry.pack(fill="x", padx=10, pady=(0, 5))
        self.setup_dnd(self.folder_path_entry)
        ctk.CTkButton(main_frame, text="Durchsuchen...", command=self.browse_folder).pack(anchor="e", padx=10, pady=(0, 20))

        # Eingabe: Excel-Datei
        ctk.CTkLabel(main_frame, text="2. Excel-Datei", font=("Arial", 14, "bold")).pack(anchor="w", padx=10)
        self.csv_path_entry = ctk.CTkEntry(main_frame, placeholder_text="Excel-Datei hierher ziehen oder auf 'Durchsuchen' klicken")
        self.csv_path_entry.pack(fill="x", padx=10, pady=(0, 5))
        self.setup_dnd(self.csv_path_entry)
        ctk.CTkButton(main_frame, text="Durchsuchen...", command=self.browse_csv).pack(anchor="e", padx=10, pady=(0, 20))
        
        # Spracheinstellung
        ctk.CTkLabel(main_frame, text="3. Sprachen auswählen", font=("Arial", 14, "bold")).pack(anchor="w", padx=10)
        self.language_menu = ctk.CTkOptionMenu(main_frame, values=["Deutsch", "English", "Polski", "Lietuvių"], anchor="w")
        self.language_menu.pack(fill="x", padx=10, pady=(0, 20))

        # Start-Button
        self.start_button = ctk.CTkButton(main_frame, text="Verarbeitung starten", font=("Arial", 16, "bold"), command=self.start_processing)
        self.start_button.pack(fill="x", padx=10, pady=10, ipady=10)

        # Log-Ausgabe
        ctk.CTkLabel(main_frame, text="Live-Protokoll", font=("Arial", 14, "bold")).pack(anchor="w", padx=10, pady=(10, 0))
        self.log_textbox = ctk.CTkTextbox(main_frame, state="disabled", wrap="word")
        self.log_textbox.pack(fill="both", expand=True, padx=10, pady=10)

    def setup_dnd(self, widget):
        widget.drop_target_register(DND_FILES)
        widget.dnd_bind('<<Drop>>', lambda e: self.on_drop(e, widget))

    def on_drop(self, event, widget):
        path = event.data.replace("{", "").replace("}", "")
        widget.delete(0, "end")
        widget.insert(0, path)

    def browse_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.folder_path_entry.delete(0, "end")
            self.folder_path_entry.insert(0, path)

    def browse_csv(self):
        path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
        if path:
            self.csv_path_entry.delete(0, "end")
            self.csv_path_entry.insert(0, path)

    def start_processing(self):
        folder_path = self.folder_path_entry.get()
        csv_path = self.csv_path_entry.get()
        selected_language = self.language_menu.get()

        if not folder_path or not os.path.isdir(folder_path):
            self.log("❌ Bitte einen gültigen Bilder-Ordner angeben.")
            return
        if not csv_path or not os.path.isfile(csv_path):
            self.log("❌ Bitte eine gültige Excel-Datei angeben.")
            return

        output_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile="catalog_results_multilang.xlsx",
            title="Speicherort für Ergebnisdatei wählen"
        )
        if not output_path:
            self.log("⚠️ Kein Speicherort gewählt, Verarbeitung abgebrochen.")
            return

        config = ProcessingConfig(
            input_path=folder_path,
            csv_path=csv_path,
            output_path=output_path,
            languages=[selected_language]
        )

        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")

        self.start_button.configure(state="disabled", text="Verarbeitung läuft...")

        self.processing_thread = threading.Thread(
            target=run_processing_logic,
            args=(config, self.log_queue),
            daemon=True
        )
        self.processing_thread.start()

    def log(self, message):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", message + "\n")
        self.log_textbox.yview_moveto(1.0)
        self.log_textbox.configure(state="disabled")

    def update_log_widget(self):
        try:
            while not self.log_queue.empty():
                message = self.log_queue.get_nowait()
                if message == "FINISHED":
                    self.start_button.configure(state="normal", text="Verarbeitung starten")
                else:
                    self.log(message)
        except queue.Empty:
            pass
        self.after(100, self.update_log_widget)


# ==============================
# Einstiegspunkt
# ==============================
if __name__ == "__main__":
    app = App()
    app.mainloop()
