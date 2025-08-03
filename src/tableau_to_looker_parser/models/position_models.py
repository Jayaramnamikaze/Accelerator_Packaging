"""
Position and styling models for dashboard elements.

Contains universal positioning and styling models that work for all dashboard elements
(worksheets, filters, text, etc.). Uses normalized 0-1 coordinate system for responsiveness.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class Position(BaseModel):
    """
    Universal position model for all dashboard elements.

    Uses normalized 0-1 coordinates for responsive design:
    - 0,0 = top-left corner
    - 1,1 = bottom-right corner
    - width/height as fraction of container
    """

    x: float = Field(
        ..., ge=0, le=1, description="X position (0=left edge, 1=right edge)"
    )
    y: float = Field(
        ..., ge=0, le=1, description="Y position (0=top edge, 1=bottom edge)"
    )
    width: float = Field(
        ..., ge=0, le=1, description="Width as fraction of container (0-1)"
    )
    height: float = Field(
        ..., ge=0, le=1, description="Height as fraction of container (0-1)"
    )

    # Z-index for overlapping elements
    z_index: int = Field(
        default=0, description="Stacking order (higher values appear in front)"
    )

    # Responsive design overrides
    mobile: Optional["Position"] = Field(
        None, description="Mobile-specific position override"
    )
    tablet: Optional["Position"] = Field(
        None, description="Tablet-specific position override"
    )

    def to_lookml_grid(
        self, grid_width: int = 24, grid_height: int = 20
    ) -> Dict[str, int]:
        """
        Convert normalized position to LookML grid coordinates.

        Args:
            grid_width: LookML grid width (default 24 columns)
            grid_height: LookML grid height (default 20 rows)

        Returns:
            Dictionary with column, row, width, height for LookML
        """
        return {
            "column": max(1, int(self.x * grid_width)),
            "row": max(1, int(self.y * grid_height)),
            "width": max(1, int(self.width * grid_width)),
            "height": max(1, int(self.height * grid_height)),
        }

    def to_pixels(self, container_width: int, container_height: int) -> Dict[str, int]:
        """
        Convert normalized position to pixel coordinates.

        Args:
            container_width: Container width in pixels
            container_height: Container height in pixels

        Returns:
            Dictionary with x, y, width, height in pixels
        """
        return {
            "x": int(self.x * container_width),
            "y": int(self.y * container_height),
            "width": int(self.width * container_width),
            "height": int(self.height * container_height),
        }


class Style(BaseModel):
    """
    Universal styling model for all dashboard elements.
    Contains common styling properties that apply to any element type.
    """

    # Colors
    background_color: Optional[str] = Field(
        None, description="Background color (hex code like #ffffff)"
    )
    border_color: Optional[str] = Field(None, description="Border color (hex code)")
    font_color: Optional[str] = Field(None, description="Text/font color (hex code)")

    # Borders
    border_width: int = Field(default=0, description="Border width in pixels")
    border_style: str = Field(
        default="none", description="Border style: none, solid, dashed, dotted"
    )

    # Spacing
    margin: int = Field(default=4, description="Margin around element in pixels")
    padding: int = Field(default=0, description="Padding inside element in pixels")

    # Typography (for text elements)
    font_size: Optional[int] = Field(None, description="Font size in pixels")
    font_family: Optional[str] = Field(None, description="Font family name")
    font_weight: Optional[str] = Field(
        None, description="Font weight: normal, bold, etc."
    )
    text_align: Optional[str] = Field(
        None, description="Text alignment: left, center, right"
    )

    # Visual effects
    opacity: float = Field(
        default=1.0, ge=0, le=1, description="Element opacity (0=transparent, 1=opaque)"
    )
    shadow: Optional[str] = Field(None, description="CSS-style shadow definition")

    # Extensibility for unknown styling properties
    custom_properties: Dict[str, Any] = Field(
        default_factory=dict, description="Custom styling properties"
    )

    def to_css(self) -> Dict[str, str]:
        """
        Convert style properties to CSS-like dictionary.
        Useful for web-based LookML dashboard rendering.
        """
        css = {}

        if self.background_color:
            css["background-color"] = self.background_color
        if self.border_color and self.border_width > 0:
            css["border"] = (
                f"{self.border_width}px {self.border_style} {self.border_color}"
            )
        if self.font_color:
            css["color"] = self.font_color
        if self.font_size:
            css["font-size"] = f"{self.font_size}px"
        if self.font_family:
            css["font-family"] = self.font_family
        if self.font_weight:
            css["font-weight"] = self.font_weight
        if self.text_align:
            css["text-align"] = self.text_align
        if self.margin > 0:
            css["margin"] = f"{self.margin}px"
        if self.padding > 0:
            css["padding"] = f"{self.padding}px"
        if self.opacity < 1.0:
            css["opacity"] = str(self.opacity)
        if self.shadow:
            css["box-shadow"] = self.shadow

        return css


# Update forward references for recursive Position model
Position.model_rebuild()
