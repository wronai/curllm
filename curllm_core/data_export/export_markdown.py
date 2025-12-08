import json
import csv
import io
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from datetime import datetime

from .data_exporter import DataExporter

def export_markdown(data: Union[List[Dict], Dict], file_path: str, **kwargs) -> str:
    """Quick Markdown export"""
    return DataExporter(data).to_markdown(file_path, **kwargs)
