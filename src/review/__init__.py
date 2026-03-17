"""Review-loop automation utilities."""

from .automation import (
    ReviewAutomationError,
    collect_review_images,
    export_slides_to_images,
    export_slides_to_images_powerpoint,
    get_image_dimensions,
)
from .aspose_export import (
    ASPOSE_AVAILABLE,
    AsposeExportError,
    convert_pptx_to_pdf,
    convert_pptx_to_pngs,
    export_slides_to_images_aspose,
)

__all__ = [
    "ASPOSE_AVAILABLE",
    "AsposeExportError",
    "ReviewAutomationError",
    "collect_review_images",
    "convert_pptx_to_pdf",
    "convert_pptx_to_pngs",
    "export_slides_to_images",
    "export_slides_to_images_aspose",
    "export_slides_to_images_powerpoint",
    "get_image_dimensions",
]
