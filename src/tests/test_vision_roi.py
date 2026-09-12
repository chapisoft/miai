"""
Unit Tests for Vision, Homography Matrix Transform, and FDI Form ROI Extraction.
"""

import numpy as np
import pytest
from engines.vision.homography import HomographyTransformer
from engines.vision.roi_extractor import RoiExtractor


def test_homography_identity_transform():
    # 4 unit box corners
    src = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    dst = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]

    h_mat = HomographyTransformer.get_perspective_matrix(src, dst)
    assert h_mat.shape == (3, 3)

    # Transform midpoint
    pt = (0.5, 0.5)
    tx, ty = HomographyTransformer.transform_point(pt, h_mat)
    assert pytest.approx(tx, 0.01) == 0.5
    assert pytest.approx(ty, 0.01) == 0.5


def test_roi_extractor_field_validation():
    # Test numeric cleanup
    raw_num = " 14,250.50 kg "
    cleaned, is_valid = RoiExtractor.validate_field(raw_num, "numeric")
    assert cleaned == "14250.50"
    assert is_valid is True

    # Test alphanumeric cleanup
    raw_alpha = " po-2026_vn "
    cleaned_alpha, is_valid_alpha = RoiExtractor.validate_field(raw_alpha, "alphanumeric")
    assert cleaned_alpha == "PO-2026_VN"
    assert is_valid_alpha is True


def test_roi_extractor_fdi_template_assembly():
    mock_data = {
        "po_number": "PO-9912",
        "net_weight": "12000.0",
        "vendor_name": "Công ty Cơ khí FDI"
    }
    form_dto = RoiExtractor.extract_from_mock_image(
        template_code="FDI_INBOUND_DELIVERY_V1",
        detected_text_map=mock_data
    )
    assert form_dto.template_code == "FDI_INBOUND_DELIVERY_V1"
    assert form_dto.document_code == "PO-9912"
    assert len(form_dto.fields) > 0
