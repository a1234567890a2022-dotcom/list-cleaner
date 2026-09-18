# List Cleaner desktop application

This is the offline version of the List Cleaner. It processes files on the local computer and does not use Anvil or upload data anywhere.

## Run from Python

Install Python 3.10 or newer, open a terminal in this folder, and run:

```text
python -m pip install -r requirements.txt
python list_cleaner_app.py
```

Select CSV/XLSX files, then use either download button:

- `Download step 1` saves files ending in `_processed.csv`.
- `Download step 2` saves files ending in `_mobile_only.csv`.

For one input file, the app asks for a save filename. For multiple files, it asks for an output folder and saves each CSV separately. No ZIP files are created.

## Build a Windows EXE

On Windows with Python installed, double-click `build_windows.bat` or run it from a terminal. The result will be:

```text
dist\ListCleaner.exe
```

The generated EXE can be copied to another Windows computer. It does not require Anvil or a separate Python installation.
