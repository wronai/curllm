import json
import csv
import io
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from datetime import datetime

from .data_exporter import DataExporter

def export_excel(data: Union[List[Dict], Dict], file_path: str, **kwargs):
    """Quick Excel export"""
    return DataExporter(data).to_excel(file_path, **kwargs)
