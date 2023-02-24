import pathlib

import nibabel as nib
import numpy as np
import pytest

import niioverlay.niioverlay as niioverlay

THIS_DIR = pathlib.Path(__file__).resolve().parent
TEST_DATA_DIR = THIS_DIR / "test_data"


def perror(r_fp, t_fp):
    """
    calculate the percentage error between two nifti files; a reference and
    a test

    Based on test used in FSL Evaluation and Example Data Suite (FEEDS)

    :param r_fp: reference file
    :type r_fp: pathlib.Path
    :param t_fp: test file
    :type t_fp: pathlib.Path
    return: percentage error of r and t
    type: float
    """

    r_obj = nib.load(str(r_fp))
    # nibabel defaults to float64 so we need to explicitly check for complex
    r_type = r_obj.get_data_dtype()
    if r_type == "complex64":
        r = r_obj.get_fdata(dtype=np.complex64)
    elif r_type == "complex128":
        r = r_obj.get_fdata(dtype=np.complex128)
    elif r_type == [("R", "u1"), ("G", "u1"), ("B", "u1")]:
        r = r_obj.dataobj.get_unscaled()
        shape_4d = r.shape + (3,)
        r = r.copy().view(dtype="u1").reshape(shape_4d)
    else:
        r = r_obj.get_fdata()

    t_obj = nib.load(str(t_fp))
    t_type = t_obj.get_data_dtype()
    if t_type == "complex64":
        t = t_obj.get_fdata(dtype=np.complex64)
    elif t_type == "complex128":
        t = t_obj.get_fdata(dtype=np.complex128)
    elif t_type == [("R", "u1"), ("G", "u1"), ("B", "u1")]:
        t = t_obj.dataobj.get_unscaled()
        shape_4d = t.shape + (3,)
        t = t.copy().view(dtype="u1").reshape(shape_4d)
    else:
        t = t_obj.get_fdata()

    return 100.0 * np.sqrt(np.mean(np.square(r - t)) / np.mean(np.square(r)))


perror_path = pathlib.Path("tests/test_data/perror/")


@pytest.mark.parametrize(
    "ref_fp, test_fp, expected_output ",
    [
        (perror_path / "OneHundred.nii.gz", perror_path / "OneHundredOne.nii.gz", 1.0),
        (perror_path / "OneHundred.nii.gz", perror_path / "NinetyNine.nii.gz", 1.0),
        (
            perror_path / "OneHundred.nii.gz",
            perror_path / "NinetyNinePointFive.nii.gz",
            0.5,
        ),
        (perror_path / "OneHundred.nii.gz", perror_path / "Zero.nii.gz", 100.0),
        (
            perror_path / "OneHundred.nii.gz",
            perror_path / "OneHundredwithGaussianNoise" "SigmaOne.nii.gz",
            1.0003711823974208,
        ),
    ],
)
def test_perror(ref_fp, test_fp, expected_output):
    assert perror(ref_fp, test_fp) == expected_output


def test_check_shape_and_orientation():
    nii_obj_1 = nib.nifti1.Nifti1Image(np.ones((32, 32, 16)), np.eye(4))
    nii_obj_2 = nib.nifti1.Nifti1Image(np.ones((32, 32, 16)), 2 * np.eye(4))
    nii_obj_3 = nib.nifti1.Nifti1Image(np.ones((32, 32, 18)), np.eye(4))

    assert niioverlay.check_shape_and_orientation(nii_obj_1, nii_obj_1)
    # Different affine
    assert not niioverlay.check_shape_and_orientation(nii_obj_1, nii_obj_2)
    # Different matrix size
    assert not niioverlay.check_shape_and_orientation(nii_obj_1, nii_obj_3)


@pytest.mark.parametrize(
    "im, lo, hi, expected_output",
    [
        (
            np.array([-2, -1, 0, 1, 2]),
            0,
            1000,
            np.array([0, 250, 500, 750, 1000]),
        ),
        (
            np.array([0, 0.1, 0.2, 0.3, 0.4]),
            0,
            1000,
            np.array([0, 250, 500, 750, 1000]),
        ),
        (
            np.array([0, 500, 1000, 1500, 2000]),
            0,
            500,
            np.array([0, 125, 250, 375, 500]),
        ),
    ],
)
def test_scale(im, lo, hi, expected_output):
    assert np.allclose(niioverlay.scale(im, lo, hi), expected_output)


SCRIPT_NAME = "niioverlay"
SCRIPT_USAGE = f"usage: {SCRIPT_NAME} [-h] [-r] b m t o"


def test_prints_help_1(script_runner):
    result = script_runner.run(SCRIPT_NAME)
    assert result.success
    assert result.stdout.startswith(SCRIPT_USAGE)


def test_prints_help_2(script_runner):
    result = script_runner.run(SCRIPT_NAME, "-h")
    assert result.success
    assert result.stdout.startswith(SCRIPT_USAGE)


def test_prints_help_for_invalid_option(script_runner):
    result = script_runner.run(SCRIPT_NAME, "-!")
    assert not result.success
    assert result.stderr.startswith(SCRIPT_USAGE)


def test_missing_base(script_runner):
    result = script_runner.run(SCRIPT_NAME, "base", "map", "3", "out")
    assert not result.success
    assert result.stderr.endswith("does not exist, exiting\n")


def test_missing_map(tmp_path, script_runner):
    base_fp = tmp_path / "base.nii.gz"
    base_fp.touch()
    result = script_runner.run(SCRIPT_NAME, str(base_fp), "map", "3", "out")
    assert not result.success
    assert result.stderr.endswith("does not exist, exiting\n")


def test_mismatched_geom(tmp_path, script_runner):
    out_fp = tmp_path / "base_map_combined.nii.gz"
    base_fp = TEST_DATA_DIR / "axial.nii.gz"
    map_fp = TEST_DATA_DIR / "map_mismatched_geom.nii.gz"

    result = script_runner.run(SCRIPT_NAME, str(base_fp), str(map_fp), "1", str(out_fp))
    assert not result.success
    assert result.stderr.endswith(
        "base and map images have mismatched geometry, exiting\n"
    )


def test_niioverlay(tmp_path, script_runner):
    pthresh = 1.0
    ref_out_fp = TEST_DATA_DIR / "axial_map_thr_1.nii.gz"

    out_fp = tmp_path / "base_map_combined.nii.gz"
    base_fp = TEST_DATA_DIR / "axial.nii.gz"
    map_fp = TEST_DATA_DIR / "map.nii.gz"

    result = script_runner.run(SCRIPT_NAME, str(base_fp), str(map_fp), "1", str(out_fp))
    assert result.success

    assert perror(ref_out_fp, out_fp) < pthresh

    # Check the data is 0:4095
    overlay_obj = nib.load(out_fp)
    data = overlay_obj.get_fdata()
    assert np.min(data) == 0
    assert np.max(data) == 4095

    # check no voxels in range 2048-3072
    assert ((2048 < data) & (data < 3072)).sum() == 0

    # check count of voxels in map image
    assert np.count_nonzero(data > 2048) == 2500
    assert np.count_nonzero(data == 4095) == 100
    assert np.count_nonzero(data == 3890) == 300
    assert np.count_nonzero(data == 3686) == 500
    assert np.count_nonzero(data == 3481) == 700
    assert np.count_nonzero(data == 3277) == 900
    assert overlay_obj.get_data_dtype() == np.uint16


def test_niioverlay_rescale(tmp_path, script_runner):
    pthresh = 1.0
    ref_out_fp = TEST_DATA_DIR / "axial_map_thr_1_rescaled.nii.gz"

    out_fp = tmp_path / "base_map_combined.nii.gz"
    base_fp = TEST_DATA_DIR / "axial.nii.gz"
    map_fp = TEST_DATA_DIR / "map.nii.gz"

    result = script_runner.run(
        SCRIPT_NAME, str(base_fp), str(map_fp), "1", str(out_fp), "-r"
    )
    assert result.success

    assert perror(ref_out_fp, out_fp) < pthresh

    # Check the raw data is 0:4095 uint16
    overlay_obj = nib.load(out_fp)
    data_unscl = overlay_obj.dataobj.get_unscaled()
    assert np.min(data_unscl) == 0
    assert np.max(data_unscl) == 4095

    # check no voxels in range 2048-3072
    assert ((2048 < data_unscl) & (data_unscl < 3072)).sum() == 0

    # check count of voxels in map image
    assert np.count_nonzero(data_unscl > 2048) == 2500
    assert np.count_nonzero(data_unscl == 4095) == 100
    assert np.count_nonzero(data_unscl == 3890) == 300
    assert np.count_nonzero(data_unscl == 3686) == 500
    assert np.count_nonzero(data_unscl == 3481) == 700
    assert np.count_nonzero(data_unscl == 3277) == 900
    assert overlay_obj.get_data_dtype() == np.uint16

    # Check the scaled data
    overlay_obj = nib.load(out_fp)
    data = overlay_obj.get_fdata()
    assert np.isclose(np.min(data), -15.0146)
    assert np.isclose(np.max(data), 5)
    assert np.count_nonzero(data >= 1) == 2500
