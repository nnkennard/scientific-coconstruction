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
  if note.forum == note.replyto: # top level note
    if '2022' in note.invitation:
      return 'Reviewer' in note.signatures[0]
  else:
    return False

def get_decision(forum_note):
    decision = None
    for note in openreview.tools.iterget_notes(
        guest_client, forum=forum_note.id):
      if '2022' in forum_note.invitation:
        if 'decision' in note.content:
          decision = note.content['decision']
          break
    assert decision is not None
    return {'decision': decision}


# == PDF helpers ==============================================================

def get_binary(note):
    try:  # try to get the PDF for this paper revision
        pdf_binary = guest_client.get_pdf(note.id, is_reference=True)
        pdf_status = PDFStatus.AVAILABLE
    except openreview.OpenReviewException as e:
        pdf_status = PDF_ERROR_STATUS_LOOKUP[e.args[0]["name"]]
        pdf_binary = None
    return pdf_status, pdf_binary


def get_last_valid_reference(references):
    for r in reversed(references):
        status, binary = get_binary(r)
        if status == PDFStatus.AVAILABLE:
            return (r, binary)
    return None, None


