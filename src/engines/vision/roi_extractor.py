"""
ROI (Region of Interest) Extractor for FDI Form Stations.
Crops designated bounding boxes based on registered form templates and applies schema constraints.
"""

from typing import List, Dict, Any, Tuple, TypedDict
import re
from schemas.vision import FdiFormDto, FdiFieldDto
from core.constants import FDIProfileType


class TemplateField(TypedDict):
    key: str
    label: str
    box: Tuple[float, float, float, float]
    type: str


class FormTemplate(TypedDict):
    partner_profile: FDIProfileType
    fields: List[TemplateField]


class RoiExtractor:
    """Manages coordinate maps and schema validations for bilingual industrial forms."""

    # Built-in template coordinate registry (Normalized 0.0 - 1.0 coordinates)
    TEMPLATES: Dict[str, FormTemplate] = {
        "FDI_INBOUND_DELIVERY_V1": {
            "partner_profile": FDIProfileType.VIET_ENGLISH,
            "fields": [
                {"key": "po_number", "label": "PO Number / Số đơn hàng", "box": (0.7, 0.05, 0.95, 0.1), "type": "alphanumeric"},
                {"key": "delivery_date", "label": "Delivery Date / Ngày giao", "box": (0.7, 0.11, 0.95, 0.15), "type": "date"},
                {"key": "vendor_name", "label": "Vendor Name / Nhà cung cấp", "box": (0.2, 0.15, 0.6, 0.2), "type": "text"},
                {"key": "net_weight", "label": "Net Weight / Trọng lượng tịnh", "box": (0.7, 0.7, 0.9, 0.75), "type": "numeric"},
                {"key": "gross_weight", "label": "Gross Weight / Trọng lượng cả bì", "box": (0.7, 0.76, 0.9, 0.81), "type": "numeric"},
                {"key": "driver_name", "label": "Driver / Tài xế", "box": (0.2, 0.85, 0.5, 0.9), "type": "text"}
            ]
        },
        "FDI_WEIGHT_SCALE_V1": {
            "partner_profile": FDIProfileType.VIET_CHINESE,
            "fields": [
                {"key": "vehicle_plate", "label": "Vehicle Plate / 车牌号 / Biển số xe", "box": (0.2, 0.1, 0.5, 0.15), "type": "alphanumeric"},
                {"key": "first_weight", "label": "First Weight / 初重 / Cân lần 1", "box": (0.6, 0.3, 0.9, 0.35), "type": "numeric"},
                {"key": "second_weight", "label": "Second Weight / 二重 / Cân lần 2", "box": (0.6, 0.36, 0.9, 0.41), "type": "numeric"},
                {"key": "cargo_weight", "label": "Cargo Net / 净重 / Khối lượng hàng", "box": (0.6, 0.42, 0.9, 0.47), "type": "numeric"}
            ]
        }
    }

    @classmethod
    def validate_field(cls, value: str, field_type: str) -> Tuple[str, bool]:
        """Enforces schema constraints and cleans common OCR artifacts."""
        val = value.strip()
        if not val:
            return "", False

        if field_type == "numeric":
            # Strip letters and keep digits and decimal point
            cleaned = re.sub(r"[^\d.]", "", val)
            return cleaned, bool(cleaned)

        elif field_type == "alphanumeric":
            cleaned = re.sub(r"[^\w\-]", "", val).upper()
            return cleaned, bool(cleaned)

        return val, True

    @classmethod
    def extract_from_mock_image(
        cls,
        template_code: str,
        detected_text_map: Dict[str, str],
        execution_time_ms: float = 120.0
    ) -> FdiFormDto:
        """Assembles extracted fields into FdiFormDto."""
        tpl = cls.TEMPLATES.get(template_code, cls.TEMPLATES["FDI_INBOUND_DELIVERY_V1"])
        fields_dto: List[FdiFieldDto] = []

        for field_def in tpl["fields"]:
            k = field_def["key"]
            raw_val = detected_text_map.get(k, "")
            cleaned_val, is_valid = cls.validate_field(raw_val, field_def["type"])

            fields_dto.append(
                FdiFieldDto(
                    field_key=k,
                    field_label=field_def["label"],
                    extracted_value=cleaned_val,
                    confidence=0.98 if is_valid else 0.75,
                    is_valid=is_valid
                )
            )

        return FdiFormDto(
            template_code=template_code,
            partner_profile=tpl["partner_profile"],
            document_code=detected_text_map.get("po_number") or detected_text_map.get("vehicle_plate"),
            fields=fields_dto,
            has_signature=True,
            processing_time_ms=execution_time_ms
        )


roi_extractor = RoiExtractor()

