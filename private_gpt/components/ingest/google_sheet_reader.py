import gspread
from llama_index.core.readers.base import BaseReader
from llama_index.core.schema import Document
from pathlib import Path

class GoogleSheetReader(BaseReader):
    """Google Sheet reader."""

    def load_data(self, file_path: Path, sheet_name: str = None):
        """Load data from a Google Sheet."""
        # Authenticate with Google
        gc = gspread.service_account()

        # Open the spreadsheet
        spreadsheet = gc.open_by_key(file_path.stem)

        # Select the worksheet
        if sheet_name:
            worksheet = spreadsheet.worksheet(sheet_name)
        else:
            worksheet = spreadsheet.sheet1

        # Get all the data from the worksheet
        data = worksheet.get_all_records()

        # Convert the data to a list of documents
        documents = [Document(text=str(row)) for row in data]

        return documents
