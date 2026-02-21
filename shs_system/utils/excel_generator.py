# This file contains Excel generation utilities
# The main functionality is in pdf_generator.py for consistency

from .pdf_generator import generate_excel_from_data

# Re-export the function for backward compatibility
__all__ = ["generate_excel_from_data"]
