import logging

import pytest

from panimg.exceptions import ValidationError
from panimg.image_builders.metaio_utils import load_sitk_image
from panimg.models import ExtraMetaData, SimpleITKImage
from tests import RESOURCE_PATH


@pytest.mark.parametrize(
    "vr,valid,invalid",
    (
        (
            "AS",
            ("000D", "123W", "456M", "789Y"),
            ("1Y", "12D", "1234D", "123"),
        ),
        ("CS", ("M", " A_A", "", "A" * 16), ("a", "A" * 17, "\\")),
        (
            "DA",
            ("20210923", "12341231", ""),
            (
                "12345678",
                "a",
                "1",
                "1234567",
                "2021923",
                "2021010a",
                "123456789",
                "20210229",
                "20210931",
                "12341231123456",
            ),
        ),
        (
            "LO",
            ("", "a" * 64, "😄", "😄" * 64),
            ("a" * 65, "\\", "😄" * 65, r"a\a"),
        ),
        (
            "PN",
            ("", "a" * 324, "😄", "😄" * 324),
            ("a" * 325, "\\", "😄" * 325, r"a\a"),
        ),
        (
            "UI",
            ("", "1.0", "0.0.0.0", "1." * 32),
            ("1." * 33, "a", "😄.😄", "1.2.+.a"),
        ),
    ),
)
def test_dicom_vr_validation(vr, valid, invalid):
    md = ExtraMetaData("Test", vr, "test")
    for t in valid:
        md.validate_value(t)

    for t in invalid:
        with pytest.raises(ValidationError):
            md.validate_value(t)


@pytest.mark.parametrize(
    ["key", "value"],
    [
        ("PatientID", "a" * 65),
        ("PatientName", "a" * 325),
        ("PatientBirthDate", "invalid date"),
        ("PatientAge", "invalid age"),
        ("PatientSex", "invalid sex"),
        ("StudyDate", "invalid date"),
        ("StudyInstanceUID", "invalid uid"),
        ("SeriesInstanceUID", "invalid uid"),
        ("StudyDescription", "a" * 65),
        ("SeriesDescription", "a" * 65),
    ],
)
def test_built_image_invalid_headers(tmpdir, caplog, key, value):
    src = RESOURCE_PATH / "image3x4-extra-stuff.mhd"
    sitk_image = load_sitk_image(src)
    sitk_image.SetMetaData(key, value)
    result = SimpleITKImage(
        image=sitk_image,
        name=src.name,
        consumed_files={src},
        spacing_valid=True,
    )
    result.save(output_directory=tmpdir)
    assert len(caplog.records) == 1
    warning = caplog.records[0]
    assert warning.levelno == logging.WARNING
    assert "ValidationError" in warning.msg
