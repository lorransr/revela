"""Decode photos in the sRGB color space shared by review and print."""
from io import BytesIO

from PIL import Image, ImageCms, ImageOps

_SRGB = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB"))
SRGB_PROFILE = _SRGB.tobytes()


def open_srgb(path, size):
    """Decode a photo with its EXIF orientation and convert its ICC colors to sRGB."""
    with Image.open(path) as source:
        source.draft("RGB", (size, size))  # Reduce JPEG decode work when the output is smaller.
        im = ImageOps.exif_transpose(source)
    icc = im.info.get("icc_profile")
    if icc:
        # Indexed PNGs carry an RGB profile for their palette, not for their indices.
        if im.mode == "P":
            im = im.convert("RGB")
        try:
            profile = ImageCms.ImageCmsProfile(BytesIO(icc))
            return ImageCms.profileToProfile(im, profile, _SRGB, outputMode="RGB")
        except (OSError, ImageCms.PyCMSError):
            # ponytail: treat unusable profiles like untagged photos instead of failing the book.
            pass
    return im.convert("RGB")
