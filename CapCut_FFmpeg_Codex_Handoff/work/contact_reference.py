from align import MEDIA, ROOT, frames
from PIL import Image, ImageDraw

TIMES = (0, 0.1, 0.2, 0.3, 0.5, 0.8, 1, 1.5, 2)
ref = frames(MEDIA / "capcut_export_test.mp4", 270, 360, 2.1)
src = frames(MEDIA / "source_original_compre_juguetes.mp4", 270, 480, 2.2)
sheet = Image.new("RGB", (270 * len(TIMES), 744), "#151515")
draw = ImageDraw.Draw(sheet)
for i, t in enumerate(TIMES):
    sheet.paste(Image.fromarray(ref[round(t * 30)]), (i * 270, 24))
    source = Image.fromarray(src[round(t * 1.02 * 30)]).transpose(
        Image.Transpose.FLIP_LEFT_RIGHT
    )
    source.thumbnail((270, 336))
    sheet.paste(source, (i * 270 + (270 - source.width) // 2, 408))
    draw.text((i * 270 + 8, 6), f"CapCut {t:.2f}s", fill="white")
    draw.text((i * 270 + 8, 390), "Nguon da lat", fill="white")
sheet.save(ROOT / "artifacts/reference_source_sheet.jpg", quality=95)
