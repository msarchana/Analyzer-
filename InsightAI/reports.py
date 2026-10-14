from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from xml.sax.saxutils import escape

def make_pdf_report(result, username="User", source="Manual input"):
    buff = BytesIO()
    doc = SimpleDocTemplate(buff, pagesize=A4, rightMargin=18*mm, leftMargin=18*mm,
                            topMargin=18*mm, bottomMargin=18*mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="SmallNote", parent=styles["BodyText"], fontSize=8, leading=11, textColor=colors.HexColor("#596579")))
    story = [
        Paragraph("InsightAI", styles["Title"]),
        Paragraph("Intelligent Text Analytics & Context Understanding", styles["Heading2"]),
        Spacer(1, 5*mm),
        Paragraph(f"Prepared for: {escape(str(username))}", styles["BodyText"]),
        Paragraph(f"Source: {escape(str(source))}", styles["BodyText"]),
        Spacer(1, 5*mm),
        Paragraph("Analysis summary", styles["Heading1"])
    ]
    data = [
        ["Measure", "Result"],
        ["Sentiment", result["sentiment"].title()],
        ["Sentiment confidence", f'{result["sentiment_score"]:.1%}'],
        ["Predicted topic", result["topic"]],
        ["Topic confidence", f'{result["topic_score"]:.1%}'],
        ["Word count", str(result["word_count"])],
        ["Character count", str(result["character_count"])],
        ["Keywords", ", ".join(result["keywords"]) or "No keywords found"],
    ]
    table = Table(data, colWidths=[55*mm, 105*mm])
    table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#16233F")),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#D8DFEA")),
        ("BACKGROUND",(0,1),(-1,-1),colors.HexColor("#F6F8FC")),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("PADDING",(0,0),(-1,-1),8),
    ]))
    story.extend([table, Spacer(1, 6*mm), Paragraph("Text preview", styles["Heading2"]),
                  Paragraph(escape(result["text"][:1800]), styles["BodyText"]), Spacer(1, 4*mm),
                  Paragraph("Model scores are estimates and do not guarantee correctness. This report is for informational and educational use, not professional decision-making.", styles["SmallNote"])])
    doc.build(story)
    return buff.getvalue()
