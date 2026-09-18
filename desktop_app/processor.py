import re
from pathlib import Path

import pandas as pd


CONCEPTUAL_COLUMNS = [
    "first name", "last name", "property address", "property street address",
    "street address", "city", "state", "zip", "phone number", "phone 1",
    "phone type 1", "phone 2", "phone type 2", "phone 3", "phone type 3",
    "phone 4", "phone type 4", "phone 5", "phone type 5",
]

EXCLUSION_PATTERNS = [
    "owner2", "owner3", "owner4", "owner5", "mailing", "mortgage",
    "foreclosure", "absentee", "matched", "person2", "person3", "relative",
    "inputmailing", "realestateagent", "address2", "streetaddress2", "zip5",
    "buyerphone",
]


def normalize_column_name(value):
    return "".join(character.lower() for character in str(value) if character.isalnum())


def _phone_number_pattern(pattern):
    match = re.fullmatch(r"phone([1-5])", normalize_column_name(pattern))
    return int(match.group(1)) if match else None


def _phone_type_pattern(pattern):
    match = re.fullmatch(r"phonetype([1-5])", normalize_column_name(pattern))
    return int(match.group(1)) if match else None


def does_pattern_match_column(pattern_keyword, column_name):
    pattern = normalize_column_name(pattern_keyword)
    column = normalize_column_name(column_name)
    phone_number_index = _phone_number_pattern(pattern)
    if phone_number_index is not None:
        return "type" not in column and re.search(
            rf"phone(?:number)?{phone_number_index}(?!\d)", column
        ) is not None
    phone_type_index = _phone_type_pattern(pattern)
    if phone_type_index is not None:
        return "phone" in column and "type" in column and re.search(
            rf"{phone_type_index}(?!\d)", column
        ) is not None
    if pattern == "phonenumber":
        return "phone" in column and "type" not in column and (
            "number" in column or column == "phone"
        )
    return pattern in column


def select_columns(dataframe):
    selected = [
        column for column in dataframe.columns
        if not any(exclusion in normalize_column_name(column) for exclusion in EXCLUSION_PATTERNS)
        and any(does_pattern_match_column(pattern, column) for pattern in CONCEPTUAL_COLUMNS)
    ]
    ordered = []
    added = set()
    for pattern in CONCEPTUAL_COLUMNS:
        matching = sorted(
            (column for column in selected if column not in added
             and does_pattern_match_column(pattern, column)),
            key=lambda value: str(value).lower(),
        )
        ordered.extend(matching)
        added.update(matching)
    return ordered


def _phone_type_pairs(columns):
    pairs = []
    for index in range(1, 6):
        phone_column = next(
            (column for column in columns
             if "type" not in normalize_column_name(column)
             and re.search(rf"phone(?:number)?{index}(?!\d)", normalize_column_name(column))),
            None,
        )
        type_column = next(
            (column for column in columns
             if "phone" in normalize_column_name(column)
             and "type" in normalize_column_name(column)
             and re.search(rf"{index}(?!\d)", normalize_column_name(column))),
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
    for column in [
        column for column in dataframe.columns
        if "phone" in normalize_column_name(column)
        and "type" not in normalize_column_name(column)
    ]:
        formatted_values = dataframe[column].apply(_format_phone_value)
        dataframe[column] = formatted_values
    return dataframe


def _apply_mobile_filter(dataframe):
    for column in [
        column for column in dataframe.columns
        if normalize_column_name(column) in ("phone", "phonenumber")
    ]:
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
        column for column in dataframe.columns
        if "phone" in normalize_column_name(column)
        and "type" in normalize_column_name(column)
    ]
    return dataframe.drop(columns=type_columns, errors="ignore")


def read_input(path):
    path = Path(path)
    if path.suffix.lower() == ".xlsx":
        return pd.read_excel(path, engine="openpyxl")
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path, low_memory=False)
    raise ValueError("Only CSV and XLSX files are supported.")


def process_file(path, mobile_only=False):
    dataframe = read_input(path)
    columns = select_columns(dataframe)
    if not columns:
        raise ValueError("No matching columns were found.")
    cleaned = dataframe[columns].copy()
    if mobile_only:
        cleaned = _apply_mobile_filter(cleaned)
    return _format_phone_columns(cleaned)


def output_filename(input_path, mobile_only=False):
    path = Path(input_path)
    suffix = "_mobile_only" if mobile_only else "_processed"
    return f"{path.stem}{suffix}.csv"
