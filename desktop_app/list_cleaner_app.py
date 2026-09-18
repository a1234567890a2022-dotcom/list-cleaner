import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from processor import output_filename, process_file


class ListCleanerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("List Cleaner")
        self.geometry("760x520")
        self.minsize(640, 440)
        self.selected_files = []
        self.status_text = tk.StringVar(value="Choose CSV or XLSX files to begin.")
        self.selection_text = tk.StringVar(value="No files selected")
        self._build_ui()

    def _build_ui(self):
        outer = ttk.Frame(self, padding=28)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="List Cleaner", font=("Segoe UI", 24, "bold")).pack(anchor="w")
        ttk.Label(
            outer,
            text="Run either cleanup step independently. Files stay on your computer.",
            wraplength=680,
        ).pack(anchor="w", pady=(6, 24))

        upload_frame = ttk.LabelFrame(outer, text="1. Choose your files", padding=18)
        upload_frame.pack(fill="x", pady=(0, 14))
        ttk.Button(upload_frame, text="Choose CSV/XLSX files", command=self.choose_files).pack(anchor="w")
        ttk.Label(upload_frame, textvariable=self.selection_text).pack(anchor="w", pady=(10, 0))

        step_one = ttk.LabelFrame(outer, text="2. Download selected columns", padding=18)
        step_one.pack(fill="x", pady=(0, 14))
        ttk.Label(
            step_one,
            text="Remove excluded columns, order the requested fields, and save one CSV per input file.",
            wraplength=520,
        ).pack(side="left", fill="x", expand=True)
        ttk.Button(step_one, text="Download step 1", command=lambda: self.download_step(False)).pack(side="right")

        step_two = ttk.LabelFrame(outer, text="3. Download Mobile/Wireless phones", padding=18)
        step_two.pack(fill="x", pady=(0, 14))
        ttk.Label(
            step_two,
            text="Keep only Mobile/Wireless phones, remove phone type columns, and save one CSV per input file.",
            wraplength=520,
        ).pack(side="left", fill="x", expand=True)
        ttk.Button(step_two, text="Download step 2", command=lambda: self.download_step(True)).pack(side="right")

        ttk.Separator(outer).pack(fill="x", pady=(8, 14))
        ttk.Label(outer, textvariable=self.status_text, wraplength=680).pack(anchor="w")
        ttk.Button(outer, text="Clear selection", command=self.clear_selection).pack(anchor="w", pady=(16, 0))

    def choose_files(self):
        paths = filedialog.askopenfilenames(
            title="Choose CSV or XLSX files",
            filetypes=[
                ("CSV and XLSX files", "*.csv *.xlsx"),
                ("CSV files", "*.csv"),
                ("XLSX files", "*.xlsx"),
            ],
        )
        if paths:
            self.selected_files = list(paths)
            count = len(self.selected_files)
            self.selection_text.set(f"{count} file{'s' if count != 1 else ''} selected")
            self.status_text.set("Choose either download step.")

    def clear_selection(self):
        self.selected_files = []
        self.selection_text.set("No files selected")
        self.status_text.set("Choose CSV or XLSX files to begin.")

    def download_step(self, mobile_only):
        if not self.selected_files:
            messagebox.showwarning("No files selected", "Choose at least one CSV or XLSX file first.")
            return

        stage_name = "step 2" if mobile_only else "step 1"
        results = []
        failures = []
        for path in self.selected_files:
            try:
                results.append((path, process_file(path, mobile_only=mobile_only)))
            except (OSError, UnicodeDecodeError, ValueError) as error:
                failures.append(f"{Path(path).name}: {error}")

        if not results:
            messagebox.showerror("Processing failed", "\n".join(failures) or "No files could be processed.")
            self.status_text.set("No files could be processed.")
            return

        saved_paths = self.save_results(results, mobile_only)
        message = f"{stage_name.capitalize()} saved {len(saved_paths)} file{'s' if len(saved_paths) != 1 else ''}."
        if failures:
            message += "\nSkipped:\n" + "\n".join(failures)
        self.status_text.set(message)
        if failures:
            messagebox.showwarning("Completed with notes", message)

    def save_results(self, results, mobile_only):
        if len(results) == 1:
            input_path, dataframe = results[0]
            destination = filedialog.asksaveasfilename(
                title="Save processed CSV",
                initialfile=output_filename(input_path, mobile_only),
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
            )
            if not destination:
                return []
            dataframe.to_csv(destination, index=False, encoding="utf-8")
            return [destination]

        folder = filedialog.askdirectory(title="Choose a folder for the processed CSV files")
        if not folder:
            return []

        saved_paths = []
        used_names = set()
        for input_path, dataframe in results:
            name = output_filename(input_path, mobile_only)
            stem = Path(name).stem
            counter = 2
            while name in used_names:
                name = f"{stem}_{counter}.csv"
                counter += 1
            used_names.add(name)
            destination = self.unique_destination(Path(folder) / name)
            dataframe.to_csv(destination, index=False, encoding="utf-8")
            saved_paths.append(str(destination))
        return saved_paths

    @staticmethod
    def unique_destination(path):
        if not path.exists():
            return path
        counter = 2
        while True:
            candidate = path.with_name(f"{path.stem}_{counter}{path.suffix}")
            if not candidate.exists():
                return candidate
            counter += 1


if __name__ == "__main__":
    ListCleanerApp().mainloop()
