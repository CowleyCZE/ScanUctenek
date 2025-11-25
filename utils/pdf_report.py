from PIL import Image, ImageDraw, ImageFont
import os

def _wrap_text(draw, text, font, max_width):
    lines = []
    words = text.split()
    current = ""
    for w in words:
        test = (current + " " + w).strip()
        if draw.textlength(test, font=font) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines

def create_pdf_report(title, acceptance_msg, comparison_rows, issues, recommendations, out_path):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    width, height = 1240, 1754  # A4 @ ~150dpi
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype("arial.ttf", 42)
        font_sub = ImageFont.truetype("arial.ttf", 28)
        font_text = ImageFont.truetype("arial.ttf", 24)
    except Exception:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_text = ImageFont.load_default()

    x_margin = 80
    y = 80
    draw.text((x_margin, y), title, fill=(0,0,0), font=font_title)
    y += 70

    # Acceptance
    draw.text((x_margin, y), "Potvrzení přijetí", fill=(0,0,0), font=font_sub)
    y += 40
    for line in _wrap_text(draw, acceptance_msg, font_text, width - 2*x_margin):
        draw.text((x_margin, y), line, fill=(0,0,0), font=font_text)
        y += 30

    # Comparison table
    y += 20
    draw.text((x_margin, y), "Porovnání klíčových údajů", fill=(0,0,0), font=font_sub)
    y += 40
    col1_x = x_margin
    col2_x = x_margin + 420
    col3_x = x_margin + 820
    row_h = 34
    # headers
    draw.text((col1_x, y), "Pole", fill=(0,0,0), font=font_text)
    draw.text((col2_x, y), "Screenshot", fill=(0,0,0), font=font_text)
    draw.text((col3_x, y), "Účtenka", fill=(0,0,0), font=font_text)
    y += row_h
    draw.line([(x_margin, y), (width - x_margin, y)], fill=(0,0,0), width=1)
    for field, scr, receipt in comparison_rows:
        draw.text((col1_x, y+6), field, fill=(0,0,0), font=font_text)
        draw.text((col2_x, y+6), scr, fill=(0,0,0), font=font_text)
        draw.text((col3_x, y+6), receipt, fill=(0,0,0), font=font_text)
        y += row_h
        draw.line([(x_margin, y), (width - x_margin, y)], fill=(220,220,220), width=1)

    # Issues
    y += 20
    draw.text((x_margin, y), "Nalezené problémy / varování", fill=(0,0,0), font=font_sub)
    y += 40
    for item in issues:
        for line in _wrap_text(draw, f"- {item}", font_text, width - 2*x_margin):
            draw.text((x_margin, y), line, fill=(0,0,0), font=font_text)
            y += 30

    # Recommendations
    y += 20
    draw.text((x_margin, y), "Doporučení pro další kroky", fill=(0,0,0), font=font_sub)
    y += 40
    for rec in recommendations:
        for line in _wrap_text(draw, f"- {rec}", font_text, width - 2*x_margin):
            draw.text((x_margin, y), line, fill=(0,0,0), font=font_text)
            y += 30

    img.save(out_path, "PDF")

