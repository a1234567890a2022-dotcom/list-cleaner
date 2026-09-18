# pyright: reportMissingImports=false

import io
import re

import anvil.server
from anvil import BlobMedia
import pandas as pd


CONCEPTUAL_COLUMNS = [
    "first name",
    "last name",
    "property address",
    "property street address",
    "street address",
    "city",
    "state",
    "zip",
    "phone number",
    "phone 1",
    "phone type 1",
    "phone 2",
    "phone type 2",
    "phone 3",
    "phone type 3",
    "phone 4",
    "phone type 4",
    "phone 5",
    "phone type 5",
]

EXCLUSION_PATTERNS = [
    "owner2",
    "owner3",
    "owner4",
    "owner5",
    "mailing",
    "mortgage",
    "foreclosure",
    "absentee",
    "matched",
    "person2",
    "person3",
    "relative",
    "inputmailing",
    "realestateagent",
    "address2",
    "streetaddress2",
    "zip5",
    "buyerphone",
]


def normalize_column_name(value):
    """Return a case- and separator-insensitive column name."""
    return "".join(character.lower() for character in str(value) if character.isalnum())


def _phone_number_pattern(pattern):
    normalized = normalize_column_name(pattern)
    match = re.fullmatch(r"phone([1-5])", normalized)
    return int(match.group(1)) if match else None


def _phone_type_pattern(pattern):
    normalized = normalize_column_name(pattern)
    match = re.fullmatch(r"phonetype([1-5])", normalized)
    return int(match.group(1)) if match else None


def does_pattern_match_column(pattern_keyword, normalized_column_name):
    """Match a desired concept without confusing Phone 1 with Phone 10."""
    pattern = normalize_column_name(pattern_keyword)
    column = normalize_column_name(normalized_column_name)

    phone_number_index = _phone_number_pattern(pattern)
    if phone_number_index is not None:
        return (
            "type" not in column
            and re.search(rf"phone(?:number)?{phone_number_index}(?!\d)", column)
            is not None
        )

    phone_type_index = _phone_type_pattern(pattern)
    if phone_type_index is not None:
        return (
            "phone" in column
            and "type" in column
            and re.search(rf"{phone_type_index}(?!\d)", column) is not None
        )

    if pattern == "phonenumber":
        return "phone" in column and "type" not in column and (
            "number" in column or column == "phone"
        )

    return pattern in column


def _is_excluded(column_name):
    normalized = normalize_column_name(column_name)
    return any(pattern in normalized for pattern in EXCLUSION_PATTERNS)


def _select_columns(dataframe):
    selected = [
        column
        for column in dataframe.columns
        if not _is_excluded(column)
        and any(
            does_pattern_match_column(pattern, column)
            for pattern in CONCEPTUAL_COLUMNS
        )
    ]

    ordered = []
    added = set()
    for pattern in CONCEPTUAL_COLUMNS:
        matching_columns = sorted(
            (
                column
                for column in selected
                if column not in added
                and does_pattern_match_column(pattern, column)
            ),
            key=lambda value: str(value).lower(),
        )
        ordered.extend(matching_columns)
        added.update(matching_columns)
    return ordered


def _phone_type_pairs(columns):
    """Find numbered phone/type pairs despite common spacing/order variants."""
    pairs = []
    for index in range(1, 6):
        phone_column = next(
            (
                column
                for column in columns
                if "type" not in normalize_column_name(column)
                and re.search(
                    rf"phone(?:number)?{index}(?!\d)",
                    normalize_column_name(column),
                )
            ),
            None,
        )
        type_column = next(
            (
                column
                for column in columns
                if "phone" in normalize_column_name(column)
                and "type" in normalize_column_name(column)
                and re.search(
                    rf"{index}(?!\d)",
                    normalize_column_name(column),
                )
            ),
            None,
        )
        if phone_column and type_column:
            pairs.append((phone_column, type_column))
    return pairs


def _format_phone_value(value):
    if pd.isna(value):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, int):
        return str(value)
    return str(value)


def _format_phone_columns(dataframe):
    phone_columns = [
        column
        for column in dataframe.columns
        if "phone" in normalize_column_name(column)
        and "type" not in normalize_column_name(column)
    ]
    for column in phone_columns:
        formatted_values = dataframe[column].apply(_format_phone_value)
        dataframe[column] = formatted_values
    return dataframe


def _apply_mobile_filter(dataframe):
    generic_phone_columns = [
        column
        for column in dataframe.columns
        if normalize_column_name(column) in ("phone", "phonenumber")
    ]
    for column in generic_phone_columns:
        dataframe[column] = dataframe[column].astype("object")
        dataframe.loc[:, column] = pd.NA

    for phone_column, type_column in _phone_type_pairs(dataframe.columns):
        is_mobile_or_wireless = dataframe[type_column].astype("string").str.lower().isin(
            ["mobile", "wireless"]
        )
        keep_phone = dataframe[type_column].notna() & is_mobile_or_wireless
        dataframe[phone_column] = dataframe[phone_column].astype("object")
        dataframe[type_column] = dataframe[type_column].astype("object")
        dataframe.loc[~keep_phone, phone_column] = pd.NA
        dataframe.loc[~keep_phone, type_column] = pd.NA

    type_columns = [
        column
        for column in dataframe.columns
        if "phone" in normalize_column_name(column)
        and "type" in normalize_column_name(column)
    ]
    return dataframe.drop(columns=type_columns, errors="ignore")


def _read_uploaded_file(uploaded_file):
    filename = uploaded_file.name or "uploaded_file.csv"
    raw_file = io.BytesIO(uploaded_file.get_bytes())
    if filename.lower().endswith(".xlsx"):
        return filename, pd.read_excel(raw_file, engine="openpyxl")
    if filename.lower().endswith(".csv"):
        return filename, pd.read_csv(raw_file, low_memory=False)
    raise ValueError("only .csv and .xlsx files are supported")


def _output_media(processed_dataframes, suffix):
    downloads = []
    used_names = set()
    for filename, dataframe in processed_dataframes.items():
        base_name = _safe_stem(filename)
        output_name = f"{base_name}{suffix}.csv"
        counter = 2
        while output_name in used_names:
            output_name = f"{base_name}{suffix}_{counter}.csv"
            counter += 1
        used_names.add(output_name)
        downloads.append(
            BlobMedia(
                "text/csv",
                dataframe.to_csv(index=False).encode("utf-8"),
                name=output_name,
            )
        )
    return downloads


def _safe_stem(filename):
    stem = re.sub(r"\.(csv|xlsx?)$", "", filename, flags=re.IGNORECASE)
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._")
    return stem or "processed_file"


def _process_uploaded_files(uploaded_files, mobile_only):
    if not uploaded_files:
        return {
            "ok": False,
            "message": "Please choose at least one CSV or XLSX file.",
            "downloads": [],
            "messages": [],
        }

    processed_dataframes = {}
    messages = []
    for uploaded_file in uploaded_files:
        filename = uploaded_file.name or "uploaded_file.csv"
        try:
            filename, dataframe = _read_uploaded_file(uploaded_file)
            selected_columns = _select_columns(dataframe)
            if not selected_columns:
                messages.append(f"Skipped {filename}: no matching columns were found.")
                continue

            cleaned = dataframe[selected_columns].copy()
            if mobile_only:
                cleaned = _apply_mobile_filter(cleaned)
            cleaned = _format_phone_columns(cleaned)
            processed_dataframes[filename] = cleaned

            stage_name = "mobile-only" if mobile_only else "selected-column"
            messages.append(
                f"{filename}: {stage_name} output has {len(cleaned.columns)} columns and {len(cleaned)} rows."
            )
        except (OSError, UnicodeDecodeError, ValueError) as error:
            messages.append(f"Skipped {filename}: {error}")

    if not processed_dataframes:
        return {
            "ok": False,
            "message": "No files could be processed.",
            "downloads": [],
            "messages": messages,
        }

    suffix = "_mobile_only" if mobile_only else "_processed"
    return {
        "ok": True,
        "message": "Downloads are ready.",
        "downloads": _output_media(processed_dataframes, suffix),
        "messages": messages,
    }


@anvil.server.callable
def process_columns_files(uploaded_files):
    """Run stage 1: select/order the desired columns and download CSVs."""
    return _process_uploaded_files(uploaded_files, mobile_only=False)


@anvil.server.callable
def process_mobile_files(uploaded_files):
    """Run stage 2: keep only Mobile/Wireless phones and download CSVs."""
    return _process_uploaded_files(uploaded_files, mobile_only=True)
