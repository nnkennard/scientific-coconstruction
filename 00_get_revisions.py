import collections
import json
import openreview
import os
import scc_lib
import tqdm

Review = collections.namedtuple("Review",
                                "review_id review_content reviewer tcdate")

INITIAL, FINAL = "initial final".split()


def export_signature(note):
    (signature, ) = note.signatures
    return signature.split("/")[-1]


class ForumStatus(object):
    COMPLETE = "complete"
    NO_REVIEWS = "no_reviews"
    NO_PDF = "no_pdf"
    NO_REVISION = "no_revision"


class PDFStatus(object):
    # for paper revisions
    AVAILABLE = "available"
    DUPLICATE = "duplicate"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"


GUEST_CLIENT = openreview.Client(baseurl="https://api.openreview.net")

PDF_ERROR_STATUS_LOOKUP = {
    "ForbiddenError": PDFStatus.FORBIDDEN,
    "NotFoundError": PDFStatus.NOT_FOUND,
}


def get_binary(note):
    try:  # try to get the PDF for this paper revision
        pdf_binary = GUEST_CLIENT.get_pdf(note.id, is_reference=True)
        pdf_status = PDFStatus.AVAILABLE
    except openreview.OpenReviewException as e:
        pdf_status = PDF_ERROR_STATUS_LOOKUP[e.args[0]["name"]]
        pdf_binary = None
    return pdf_status, pdf_binary


def write_pdfs(forum_dir, initial_binary, final_binary):
    for binary, version in [(initial_binary, INITIAL), (final_binary, FINAL)]:
        assert binary is not None
        with open(f'{forum_dir}/{version}.pdf', "wb") as f:
            f.write(binary)


def get_last_valid_reference(references):
    for r in reversed(references):
        status, binary = get_binary(r)
        if status == PDFStatus.AVAILABLE:
            return (r, binary)
    return None, None


def write_metadata(forum_dir, forum, review_notes):
    pass
    # Get metareview


def retrieve_forum(forum, conference):

    # Get all reviews, find first review time
    review_notes = []
    for note in GUEST_CLIENT.get_all_notes(forum=forum.id):
        if (note.replyto == note.forum and
            ("main_review" in note.content or "review" in note.content)):
            review_notes.append(
                Review(note.id, json.dumps(note.content),
                       export_signature(note), note.tcdate))
    if not review_notes:
        return ForumStatus.NO_REVIEWS
    first_review_time = min(rev.tcdate for rev in review_notes)

    # Get all revisions
    references = sorted(
        GUEST_CLIENT.get_all_references(referent=forum.id, original=True),
        key=lambda x: x.tcdate,  # our retrieved contents are updated at tmdate
    )
    references_before_review = [
        r for r in references if r.tcdate <= first_review_time
    ]

    final_reference, final_binary = get_last_valid_reference(references)
    initial_reference, initial_binary = get_last_valid_reference(
        references_before_review)
    if final_reference is not None and initial_reference is not None:
        if not final_reference.id == initial_reference.id:
            forum_dir = f'temp_dir/{forum.id}'
            os.makedirs(forum_dir, exist_ok=True)
            write_pdfs(forum_dir, initial_binary, final_binary)
            # Write metadata
            write_metadata(forum_dir, forum, review_notes)
            return ForumStatus.COMPLETE
        else:
            return ForumStatus.NO_REVISION
    else:
        return ForumStatus.NO_PDF


def retrieve_conference(conference):
    statuses = []
    forum_notes = GUEST_CLIENT.get_all_notes(
        invitation=scc_lib.INVITATIONS[conference])
    for forum in tqdm.tqdm(forum_notes):
        status = retrieve_forum(forum, conference)
        statuses.append((forum.id, status))
    return statuses


def main():

    statuses = []
    for conference in scc_lib.Conference.ALL:
        print(conference)
        statuses += retrieve_conference(conference)


if __name__ == "__main__":
    main()
