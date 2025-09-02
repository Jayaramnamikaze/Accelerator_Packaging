"""
Field Name Mapper - Handles mapping between original Tableau field names and clean field names.

This module addresses the issue where calculated fields have captions that create clean names,
but other formulas reference them by their original Tableau internal names.
"""

import logging
import re
from typing import Dict, Optional, Set

logger = logging.getLogger(__name__)


class FieldNameMapper:
    """
    Maps between original Tableau field names and clean field names.

    Handles the scenario where calculated fields have captions that create clean names,
    but other formulas reference them by their original Tableau internal names.
    """

    def __init__(self):
        """Initialize the field name mapper."""
        # Mapping from original name to clean name
        self.original_to_clean: Dict[str, str] = {}
        # Mapping from clean name to original name (for reverse lookup)
        self.clean_to_original: Dict[str, str] = {}
        # Set of all registered field names for quick lookup
        self.registered_fields: Set[str] = set()
        # Track which fields are calculated fields
        self.calculated_fields: Set[str] = set()

    def register_field(
        self,
        original_name: str,
        clean_name: str,
        caption: Optional[str] = None,
        is_calculated: bool = False,
    ):
        """
        Register a field mapping.

        Args:
            original_name: Original Tableau field name (e.g., '[Calculation_978688514352406528]')
            clean_name: Clean field name for LookML (e.g., 'take_rate_percent')
            caption: Optional user-friendly caption
            is_calculated: Whether this field is a calculated field
        """
        # Store the main mapping
        self.original_to_clean[original_name] = clean_name
        self.clean_to_original[clean_name] = original_name
        self.registered_fields.add(original_name)
        self.registered_fields.add(clean_name)

        # Track if this is a calculated field
        if is_calculated:
            self.calculated_fields.add(clean_name)
            self.calculated_fields.add(original_name)

        # Also store with brackets for flexibility
        bracketed_original = f"[{original_name}]"
        self.original_to_clean[bracketed_original] = clean_name
        self.registered_fields.add(bracketed_original)
        if is_calculated:
            self.calculated_fields.add(bracketed_original)

        # Also store the cleaned version of the original name for better matching during parsing
        # This handles cases where the tokenizer has already cleaned the field name
        cleaned_original = original_name.lower().replace(" ", "_")
        if (
            cleaned_original != clean_name
        ):  # Only add if it's different from the clean name
            self.original_to_clean[cleaned_original] = clean_name
            self.registered_fields.add(cleaned_original)
            if is_calculated:
                self.calculated_fields.add(cleaned_original)

        # Also store the cleaned version of the bracketed name
        cleaned_bracketed = bracketed_original.lower().replace(" ", "_")
        if (
            cleaned_bracketed != clean_name
        ):  # Only add if it's different from the clean name
            self.original_to_clean[cleaned_bracketed] = clean_name
            self.registered_fields.add(cleaned_bracketed)
            if is_calculated:
                self.calculated_fields.add(cleaned_bracketed)

        logger.debug(
            f"Registered field mapping: '{original_name}' -> '{clean_name}' (calculated: {is_calculated})"
        )

    def get_clean_name(self, original_name: str) -> Optional[str]:
        """
        Get clean name for an original field name.

        Args:
            original_name: Original Tableau field name

        Returns:
            Clean field name if found, None otherwise
        """
        # Try exact match first
        if original_name in self.original_to_clean:
            return self.original_to_clean[original_name]

        # Try with brackets removed
        clean_original = original_name.strip("[]")
        if clean_original in self.original_to_clean:
            return self.original_to_clean[clean_original]

        # Try with brackets added
        bracketed_original = f"[{original_name}]"
        if bracketed_original in self.original_to_clean:
            return self.original_to_clean[bracketed_original]

        # Try case-insensitive matching
        for key, value in self.original_to_clean.items():
            if key.lower() == original_name.lower():
                return value
            if key.lower() == clean_original.lower():
                return value
            if key.lower() == bracketed_original.lower():
                return value

        return None

    def get_original_name(self, clean_name: str) -> Optional[str]:
        """
        Get original name for a clean field name.

        Args:
            clean_name: Clean field name

        Returns:
            Original field name if found, None otherwise
        """
        return self.clean_to_original.get(clean_name)

    def is_registered(self, field_name: str) -> bool:
        """
        Check if a field name is registered (either original or clean).

        Args:
            field_name: Field name to check

        Returns:
            True if the field is registered, False otherwise
        """
        return field_name in self.registered_fields

    def resolve_field_reference(self, field_reference: str) -> str:
        """
        Resolve a field reference to its clean name.

        Args:
            field_reference: Field reference from formula (e.g., '[Calculation_978688514352406528]')

        Returns:
            Clean field name if mapped, original reference if not found
        """
        # Try to get clean name for this field reference
        clean_name = self.get_clean_name(field_reference)
        if clean_name:
            logger.debug(
                f"Resolved field reference '{field_reference}' -> '{clean_name}'"
            )
            return clean_name

        # If not found, also try with the original_name field format
        # This handles cases where the field reference might be stored differently
        if field_reference in self.original_to_clean:
            clean_name = self.original_to_clean[field_reference]
            logger.debug(
                f"Resolved field reference '{field_reference}' -> '{clean_name}' (direct match)"
            )
            return clean_name

        logger.debug(
            f"No mapping found for field reference '{field_reference}', using as-is"
        )
        return field_reference

    def create_clean_name_from_caption(self, caption: str) -> str:
        """
        Create a clean field name from a caption.

        Args:
            caption: User-friendly caption (e.g., 'Take Rate %')

        Returns:
            Clean field name suitable for LookML (e.g., 'take_rate_percent')
        """
        # Convert to lowercase
        clean_name = caption.lower()

        # Handle special characters more carefully
        # Replace % with "percent" for better readability
        clean_name = clean_name.replace("%", "_percent")

        # Replace spaces and other special characters with underscores
        clean_name = re.sub(r"[^a-z0-9]+", "_", clean_name)

        # Remove duplicate underscores
        clean_name = re.sub(r"_+", "_", clean_name)

        # Remove leading/trailing underscores
        clean_name = clean_name.strip("_")

        return clean_name

    def get_all_mappings(self) -> Dict[str, str]:
        """
        Get all field mappings.

        Returns:
            Dictionary of all original name to clean name mappings
        """
        return self.original_to_clean.copy()

    def clear(self):
        """Clear all mappings."""
        self.original_to_clean.clear()
        self.clean_to_original.clear()
        self.registered_fields.clear()
        self.calculated_fields.clear()

    def __len__(self) -> int:
        """Return the number of registered mappings."""
        return len(self.original_to_clean)

    def __repr__(self) -> str:
        """String representation of the mapper."""
        return f"FieldNameMapper({len(self)} mappings)"

    def is_calculated_field(self, field_name: str) -> bool:
        """
        Check if a field is a calculated field.

        Args:
            field_name: Field name to check (can be original, clean, or any variation)

        Returns:
            True if the field is a calculated field, False otherwise
        """
        # Check if the field name itself is in the calculated fields set
        if field_name in self.calculated_fields:
            return True

        # Check if the clean name is in the calculated fields set
        clean_name = self.get_clean_name(field_name)
        if clean_name and clean_name in self.calculated_fields:
            return True

        return False


# Global instance for use across the application
field_name_mapper = FieldNameMapper()
