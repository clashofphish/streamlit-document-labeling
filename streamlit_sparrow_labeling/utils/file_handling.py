import pandas as pd
from typing import TypedDict


class ConfigDataFrame(TypedDict):
    index: int
    opportunityId: str
    attachmentId: str
    image_file_path: str
    fileName: str
    ocr_file_path: str


def load_config_dataframe(config_file: str) -> pd.DataFrame:
    """Load the configuration file and return as DataFrame."""
    df = pd.read_csv(config_file)
    # Validate the columns
    expected_columns = ConfigDataFrame.__annotations__.keys()
    if not all(column in df.columns for column in expected_columns):
        raise ValueError(
            f"DataFrame does not have the expected columns: {expected_columns}"
        )

    df.set_index("index", inplace=True)
    return df


class AnnotatedConfigDataFrame(TypedDict):
    index: int
    opportunityId: str
    attachmentId: str
    image_file_path: str
    fileName: str
    ocr_file_path: str
    class_1: str
    class_2: str
    class_3: str
    annotated_text: str
    doc_type: str


def load_annotated_config_dataframe(config_file: str) -> pd.DataFrame:
    """Load the configuration file and return as DataFrame."""
    df = pd.read_csv(config_file)
    # Validate the columns
    expected_columns = AnnotatedConfigDataFrame.__annotations__.keys()
    if not all(column in df.columns for column in expected_columns):
        raise ValueError(
            f"DataFrame does not have the expected columns: {expected_columns}"
        )

    df.set_index("index", inplace=True)
    return df
