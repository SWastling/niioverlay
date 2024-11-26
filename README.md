# niioverlay

## Synopsis
Create NIfTI overlay images by combining a base structural image with a 
coregistered map

## Usage

```bash
niioverlay [-h] b m t o
```
- `b`: base image
- `m`: map image 
- `t`: intensity threshold for map
- `o`: output image


## Options
- `-h`: show this help message and exit
- `-r`: set the rescale slope and intercept such that the voxel intensities 
are scaled back to their original values when displayed

## Description
This package can be used to combine two NIfTI images, using the following steps:

1. linearly scale the voxel values of the base image to integers in the range 
0-2047
2. threshold the map image, using the threshold provided
3. create a binary mask from the threshold map image
4. linearly scale the voxel values of the threshold map image to integers in 
the range 3072-4095
5. combine the linearly scaled base and map images by replacing the voxel values 
in the base image with the voxels from the map image at every voxel where the 
mask, created in step 3, is non-zero
6. [optional] set the rescale slope and intercept such that the intensities of 
the replaced voxels, i.e. those from the map, placed in the base, are displayed 
with their original values

The data-type of the resulting NIfTI is Unsigned Short i.e. UINT16. This file 
can be readily converted to DICOM files with a Magnetic Resonance (MR) Image 
composite Information Object Definition (IOD) with an appropriate tool. 

## Installing
1. Create a new virtual environment in which to install `niioverlay`:

    ```bash
    uv venv niioverlay-venv
    ```
   
2. Activate the virtual environment:

    ```bash
    source niioverlay-venv/bin/activate
    ```

4. Install using `uv pip`:
    ```bash
    uv pip install git+https://github.com/SWastling/niioverlay.git
    ```
   
> [!TIP]
> You can also run `niioverlay` without installing it using [uvx](https://docs.astral.sh/uv/guides/tools/) i.e. with the command `uvx --from  git+https://github.com/SWastling/niioverlay.git niioverlay`

## Alternate Implementations using FSL or MRtrix3 Tools
It is possible to produce identical results using 
[FSL](https://fsl.fmrib.ox.ac.uk/fsl/) or 
[MRtrix3](https://www.mrtrix.org/) tools as illustrated in the two bash scripts 
[niioverlay_fsl](./niioverlay_fsl) and 
[niioverlay_mrtrix3](./niioverlay_mrtrix3) included in this repository.

## License
See [MIT license](./LICENSE)


## Authors and Acknowledgements
[Stephen Wastling](mailto:stephen.wastling@nhs.net) 

The bash scripts are based on a 
[template](https://betterdev.blog/minimal-safe-bash-script-template/) written 
by Maciej Radzikowski. The bash syntax was analysed and checked for bugs using 
[ShellCheck](https://www.shellcheck.net/) written by Vidar Holen. 