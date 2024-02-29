import openreview

# == Constants ================================================================

INITIAL, FINAL = "initial", "final"


class PDFStatus(object):
    # for paper revisions
    AVAILABLE = "available"
    DUPLICATE = "duplicate"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"


class ForumStatus(object):
    COMPLETE = "complete"
    NO_REVIEWS = "no_reviews"
    NO_PDF = "no_pdf"
    NO_REVISION = "no_revision"


PDF_ERROR_STATUS_LOOKUP = {
    "ForbiddenError": PDFStatus.FORBIDDEN,
    "NotFoundError": PDFStatus.NOT_FOUND,
}

PDF_URL_PREFIX = "https://openreview.net/references/pdf?id="
INVITATION = 'ICLR.cc/2022/Conference/-/Blind_Submission'

# == Helpers ==================================================================


def export_signature(note):
    (signature, ) = note.signatures
    return signature.split("/")[-1]


def is_review(note):
    if note.forum == note.replyto:  # top level note
        if '2022' in note.invitation:
            return 'Reviewer' in export_signature(note)
    else:
        return False


def is_by_authors(note):
    if '2022' in note.invitation:
        return 'Authors' in export_signature(note)


def get_decision(forum_notes):
    decision = None
    for note in forum_notes:
        if '2022' in note.invitation and 'Decision' in note.invitation:
            decision = note.content['decision']
            break
    assert decision is not None
    return decision


# == PDF helpers ==============================================================


def get_binary(note, guest_client):
    try:  # try to get the PDF for this paper revision
        pdf_binary = guest_client.get_pdf(note.id, is_reference=True)
        pdf_status = PDFStatus.AVAILABLE
    except openreview.OpenReviewException as e:
        pdf_status = PDF_ERROR_STATUS_LOOKUP[e.args[0]["name"]]
        pdf_binary = None
    return pdf_status, pdf_binary


def get_last_valid_reference(references, guest_client):
    # Going over references in reverse order
    for r in reversed(sorted(references, key=lambda x: x.tcdate)):
        # Maybe get pdf
        status, binary = get_binary(r, guest_client)
        if status == PDFStatus.AVAILABLE:
            return (r, binary)
    # TODO: Should this give the PDF status instead? Do we care?
    return None, None
