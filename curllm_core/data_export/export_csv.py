import json
import csv
import io
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from datetime import datetime

from .data_exporter import DataExporter

def export_csv(data: Union[List[Dict], Dict], file_path: str, **kwargs) -> str:
    """Quick CSV export"""
    return DataExporter(data).to_csv(file_path, **kwargs)
