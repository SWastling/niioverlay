"""
Create NIfTI overlay images by combining a base structural image with a coregistered map
"""

import argparse
import copy
import pathlib
import sys
import importlib.metadata

import nibabel as nib
import numpy as np

__version__ = importlib.metadata.version("niioverlay")


def check_shape_and_orientation(a_obj, b_obj):
    """
    Compare the affine and matrix size in the header of two NIfTI files

    :param a_obj: first NIfTI object
    :type a_obj: nib.nifti1.Nifti1Image
    :param b_obj: second NIfTI object
    :type b_obj: nib.nifti1.Nifti1Image
    :return: True is matching, False if not
    :rtype: bool
    """

    a_affine = a_obj.header.get_best_affine()
    a_shape = a_obj.header.get_data_shape()

    b_affine = b_obj.header.get_best_affine()
    b_shape = b_obj.header.get_data_shape()

    if np.allclose(a_affine, b_affine) and (a_shape == b_shape):
        return True
    else:
        return False


def scale(im, lo, hi):
    """
    Linearly scale image intensities within range [min, max] to integers in range [lo, hi]

           (hi-lo)(x - min(x))
    f(x) = -------------------  + lo
            max(x) - min(x)

    :param im: Input image
    :type im: np.ndarray
    :param lo: min intensity of output
    :type lo: int
    :param hi: max intensity of output
    :type hi: int
    :return: image array
    :rtype: np.ndarray
    """

    im = np.nan_to_num(im)
    im = np.rint((((hi - lo) * (im - np.min(im))) / np.ptp(im)) + lo)
    im.astype(np.uint16)

    return im


def main():
    parser = argparse.ArgumentParser(
        description="Create NIfTI overlay images "
        "by combining a base structural image "
        "with a coregistered map"
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    parser.add_argument("b", type=pathlib.Path, help="base image")

    parser.add_argument("m", type=pathlib.Path, help="map image")

    parser.add_argument(
        "t",
        type=float,
        help="intensity threshold for map",
    )

    parser.add_argument("o", type=pathlib.Path, help="output image")

    parser.add_argument(
        "-r",
        help="set the rescale slope and intercept such that the voxel "
        "intensities are scaled back to their original values when displayed",
        action="store_true",
    )

    if len(sys.argv) == 1:
        sys.argv.append("-h")

    args = parser.parse_args()

    b_fp = args.b.resolve()
    if not b_fp.is_file():
        sys.stderr.write("ERROR: %s does not exist, exiting\n" % b_fp)
        sys.exit(1)

    m_fp = args.m.resolve()
    if not m_fp.is_file():
        sys.stderr.write("ERROR: %s does not exist, exiting\n" % m_fp)
        sys.exit(1)

    print("* loading data")
    b_nii_obj = nib.load(str(b_fp))
    m_nii_obj = nib.load(str(m_fp))

    if not check_shape_and_orientation(b_nii_obj, m_nii_obj):
        sys.stderr.write("base and map images have mismatched geometry, exiting\n")
        sys.exit(1)

    print("* processing base image")
    b = b_nii_obj.get_fdata()
    affine = b_nii_obj.header.get_best_affine()

    print("** scaling voxel values from 0 to 2047")
    b_scaled = scale(b, 0, 2047)

    print("* processing map")
    m = m_nii_obj.get_fdata()
    m = np.nan_to_num(m)

    print("** creating mask using threshold of %g" % args.t)
    mask = m >= args.t

    print("** scaling voxel values from 3072 to 4095")
    m_scaled = scale(m, 3072, 4095)

    print("* combining map and base image")
    overlay = copy.deepcopy(b_scaled)
    overlay[mask] = m_scaled[mask]

    o_fp = args.o.resolve()
    print("* writing %s" % o_fp)
    nii_obj = nib.nifti1.Nifti1Image(overlay, affine)
    nii_obj.set_data_dtype(np.uint16)
    if args.r:
        scl_slope = float(np.nanmax(m)) / (4095 - 3072)
        scl_inter = -3072 * scl_slope
    else:
        # explicitly set slope and intercept otherwise nibabel tries to
        # "find an optimum slope and intercept to preserve the precision of the
        # data"
        scl_slope = 1
        scl_inter = 0

    nii_obj.header.set_slope_inter(scl_slope, scl_inter)
    cal_min = (0 * scl_slope) + scl_inter
    cal_max = (4095 * scl_slope) + scl_inter
    nii_obj.header["cal_min"] = cal_min
    nii_obj.header["cal_max"] = cal_max
    nii_obj.header.set_intent(1001, name="conn index")

    nii_obj.to_filename(str(o_fp))


if __name__ == "__main__":  # pragma: no cover
    main()
