import tifffile as tiff

img = tiff.imread("results/stacked/ROI001_D13.tiff")
print("Shape:", img.shape)