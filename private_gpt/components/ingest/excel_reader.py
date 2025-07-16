import pandas as pd
from llama_index.core.readers.base import BaseReader
from llama_index.core.schema import Document
from pathlib import Path

class ExcelReader(BaseReader):
    """Excel reader."""

    def load_data(self, file_path: Path, sheet_name: str = None):
        """Load data from an Excel file."""
        # Read the Excel file
        excel_file = pd.ExcelFile(file_path)

        # Get the sheet names
        sheet_names = excel_file.sheet_names

        # Read the data from the sheets
        documents = []
        for sheet_name in sheet_names:
            df = excel_file.parse(sheet_name)
            for index, row in df.iterrows():
                documents.append(Document(text=str(row.to_dict())))

        return documents
