#!/usr/bin/env python3
"""Build merged contributor legal packet PDF for Pheo Inc."""

from pathlib import Path

from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUT = Path(__file__).resolve().parent / "pheo-contributor-agreement.pdf"

BODY_SIZE = 8.2
BODY_LEAD = 9.8


def build_pdf() -> Path:
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title="Pheo Inc. Open Source Contributor Agreement",
        author="Pheo Inc.",
    )

    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=13,
        alignment=TA_CENTER,
        spaceAfter=5,
    )
    part = ParagraphStyle(
        "PartTitle",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=11,
        spaceBefore=3,
        spaceAfter=3,
    )
    body = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=BODY_SIZE,
        leading=BODY_LEAD,
        alignment=TA_JUSTIFY,
        spaceAfter=1.5,
    )
    story = []

    def P(text: str, style=body):
        story.append(Paragraph(text, style))

    P("OPEN SOURCE CONTRIBUTOR AGREEMENT", title)
    P(
        '<b>Effective Date:</b> ____________________ &nbsp;&nbsp;|&nbsp;&nbsp; '
        '<b>Parties:</b> <b>Pheo Inc.</b> ("Company"), a Delaware corporation with principal place of business at '
        '____________________, California; and ____________________, an individual residing at '
        '____________________ ("Contributor"). This Agreement includes <b>Part I (Confidentiality)</b> and '
        "<b>Part II (Contributor License)</b>."
    )

    P("PART I — CONFIDENTIALITY AND NON-DISCLOSURE", part)
    P(
        '<b>1. Purpose.</b> Contributor may receive Company confidential information while contributing to '
        'open-source software projects maintained or designated by Company (the "Project"). Part I permits '
        "participation while protecting such information."
    )
    P(
        '<b>2. Confidential Information.</b> "Confidential Information" means non-public information disclosed by '
        "Company that is identified as confidential or should reasonably be understood as confidential, including "
        "unreleased product plans, non-public code and architectures, business and customer information, pricing, "
        "security issues, internal metrics, partnerships, and credentials. Exclusions: (a) public through no breach "
        "by Contributor; (b) lawfully known without restriction before disclosure; (c) lawfully received from a "
        "third party without breach; (d) independently developed without use of Confidential Information."
    )
    P(
        '<b>3. Open Source Carve-Out.</b> Part I does not restrict Contributor from: (a) contributing <b>original</b> '
        "code or documentation to the Project under the applicable open-source license(s); (b) using general "
        "skills and unaided memory; or (c) unrelated personal or open-source work—provided none includes, "
        "incorporates, references, or derives from Confidential Information. Contributor shall not publish Confidential "
        "Information in any public repository, forum, or other public medium without prior written consent."
    )
    P(
        "<b>4. Obligations.</b> Contributor shall: use Confidential Information only for the Purpose; protect it with "
        "reasonable care; not disclose it without consent; not copy or distribute except as needed for the Purpose; "
        "notify Company of unauthorized use; and not export it outside the U.S. without consent except via "
        "Company-approved Project tools."
    )
    P(
        "<b>5. Compelled Disclosure.</b> If legally required to disclose Confidential Information, Contributor shall "
        "(to the extent permitted) provide Company prompt written notice and reasonable cooperation so Company may "
        "seek a protective order or other remedy. Contributor may disclose only the portion legally required."
    )
    P(
        "<b>6. Return or Destruction.</b> Upon Company's written request, or upon completion or termination of "
        "participation, Contributor shall promptly return or destroy all Confidential Information and copies, except "
        "one archival copy solely as required by applicable law, subject to continuing confidentiality obligations."
    )
    P(
        "<b>7. No License; No Obligation.</b> Except as in Part II, no IP license is granted. No employment or "
        "commercial relationship is created. Either Party may terminate Part I on ten (10) days' notice."
    )
    P(
        '<b>8. Warranties; Term; Remedies.</b> Confidential Information is "AS IS." Part I runs two (2) years from '
        "the Effective Date. Obligations survive five (5) years from disclosure (trade secrets: as long as protected). "
        "Company may seek injunctive relief for breach."
    )

    story.append(PageBreak())
    P("PART II — INDIVIDUAL CONTRIBUTOR LICENSE", part)
    P(
        '<b>1. Definitions.</b> "Contribution" means original work Contributor submits to the Project (PR, patch, '
        'commit, issue, etc.). "Submit" means transfer via repository, tracker, or other Company-designated channel.'
    )
    P(
        "<b>2. Copyright License.</b> Contributor grants Company and downstream recipients a perpetual, worldwide, "
        "non-exclusive, royalty-free, irrevocable license to reproduce, prepare derivative works of, display, perform, "
        "sublicense, and distribute Contributions under the open-source license(s) governing the Project and any "
        "other license Company may apply."
    )
    P(
        "<b>3. Patent License.</b> Contributor grants a perpetual, worldwide, non-exclusive, royalty-free, irrevocable "
        "patent license for Contributions, limited to claims necessarily infringed by the Contribution alone or with the "
        "Project. Patent licenses terminate as to any entity that files litigation alleging Project/Contribution infringement."
    )
    P(
        "<b>4. Representations.</b> Contributor represents: (a) Contributions are original or properly licensed; "
        "(b) no Confidential Information or third-party materials without permission; (c) no known IP violation; and "
        "(d) Contributor is at least eighteen (18) years of age, or has required parental or guardian consent."
    )
    P(
        "<b>5. Public Contributions.</b> No non-public Company information in public Contributions. Part I remains in effect."
    )
    P(
        "<b>6. Voluntary.</b> Participation is unpaid unless a separate written agreement says otherwise. No employment, "
        "agency, partnership, or joint venture is created."
    )
    P(
        "<b>7. Moral Rights; Disclaimer; Liability.</b> To the extent permitted by law, Contributor waives moral rights "
        "in Contributions. Company may include Contributor's name in attribution where customary. Contributions are "
        '"AS IS" without warranties. Contributor is not liable for indirect, incidental, special, consequential, or '
        "punitive damages arising from this Agreement or any Contribution."
    )
    P(
        "<b>8. Term; Termination.</b> Part II applies to Contributions made on or after the Effective Date until "
        "terminated. Contributor may terminate on thirty (30) days' written notice to Company. Termination does not "
        "revoke licenses for Contributions submitted before termination. Surviving sections remain in effect for prior Contributions."
    )
    P(
        "<b>9. General (Both Parts).</b> California law governs; exclusive venue: Santa Clara County. This Agreement "
        "is the entire agreement between the Parties regarding Contributor's participation in the Project. Amendments "
        "in writing. Contributor may not assign without consent; Company may assign to a successor. Severability applies. "
        "Counterparts and e-signatures permitted."
    )

    story.append(PageBreak())
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=0.4, color="black"))
    story.append(Spacer(1, 8))

    P("SIGNATURES", part)
    story.append(Spacer(1, 2))
    sig_data = [
        ["PHEO INC.", "CONTRIBUTOR"],
        ["By: ____________________________", "Signature: ____________________________"],
        ["Name: ____________________________", "Printed Name: ____________________________"],
        ["Title: ____________________________", "Email: ____________________________"],
        ["Date: ____________________________", "Date: ____________________________"],
    ]
    sig_table = Table(sig_data, colWidths=[3.35 * inch, 3.35 * inch])
    sig_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.8),
                ("FONTNAME", (0, 0), (1, 0), "Helvetica-Bold"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(sig_table)

    doc.build(story)
    return OUT


if __name__ == "__main__":
    path = build_pdf()
    print(f"Wrote {path}")
