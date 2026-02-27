"""Review-loop automation utilities."""

from .automation import (
    ReviewAutomationError,
    collect_review_images,
    export_slides_to_images,
    export_slides_to_images_powerpoint,
    get_image_dimensions,
)

__all__ = [
    "ReviewAutomationError",
    "collect_review_images",
    "export_slides_to_images",
    "export_slides_to_images_powerpoint",
    "get_image_dimensions",
]
