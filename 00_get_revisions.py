import argparse
import collections
import json
import openreview
import os
import stanza
import tqdm

import scc_lib

parser = argparse.ArgumentParser(description='')
parser.add_argument('-o',
                    '--output_dir',
                    type=str,
                    help='directory to dump pdfs',
                    required=True)
parser.add_argument("-c",
                    "--conference",
                    type=str,
                    choices=scc_lib.Conference.ALL,
                    help="conference_year, e.g. iclr_2022",
                    required=True)
parser.add_argument('-s',
                    '--status_file_prefix',
                    default='./statuses/status_',
                    type=str,
                    help='prefix for tsv file with status of all forums')

# == OpenReview-specific stuff ===============================================


def export_signature(note):
    (signature, ) = note.signatures
    return signature.split("/")[-1]


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

PDF_URL_PREFIX = "https://openreview.net/references/pdf?id="
FORUM_URL_PREFIX = "https://openreview.net/forum?id="

INVITATIONS = {
    f"iclr_{year}": f"ICLR.cc/{year}/Conference/-/Blind_Submission"
        for year in range(2018, 2023)
        }

# == Other helpers ===========================================================

Review = collections.namedtuple("Review",
                                "review_id sentences rating reviewer tcdate")

INITIAL, FINAL = "initial final".split()


class ForumStatus(object):
    COMPLETE = "complete"
    NO_REVIEWS = "no_reviews"
    NO_PDF = "no_pdf"
    NO_REVISION = "no_revision"


SENTENCIZE_PIPELINE = stanza.Pipeline("en", processors="tokenize")

# ============================================================================


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


def get_review_sentences_and_rating(note):
    if 'review' in note.content:
        review_text = note.content['review']
        rating = note.content['rating']
    else:
        review_text = note.content['main_review']
        rating = note.content['recommendation']
    return [sent.text
            for sent in SENTENCIZE_PIPELINE(review_text).sentences], rating


def write_metadata(forum_dir, forum, conference, initial_id, final_id,
decision,
                   review_notes):
    reviews = []
    for review_note in review_notes:
        review_sentences, rating = get_review_sentences_and_rating(review_note)
        reviews.append(
            Review(review_note.id, review_sentences, rating,
                   export_signature(review_note),
                   review_note.tcdate)._asdict())
    with open(f'{forum_dir}/metadata.json', 'w') as f:
        f.write(
            json.dumps(
                {
                    'identifier': forum.id,
                    'reviews': reviews,
                    'decision': decision,
                    'conference': conference,
                    'urls': {
                        'forum': f'{FORUM_URL_PREFIX}{forum.id}',
                        'initial': f'{PDF_URL_PREFIX}{initial_id}',
                        'final': f'{PDF_URL_PREFIX}{final_id}',
                    }
                },
                indent=2))


def retrieve_forum(forum, conference, output_dir):

    # Retrieve all reviews from the forum
    review_notes = []
    for note in GUEST_CLIENT.get_all_notes(forum=forum.id):
        if (note.replyto == note.forum and
            ("main_review" in note.content or "review" in note.content)):
            # ICLR 2022 has main_review as a field, others have review
            review_notes.append(note)

    # Retrieve decision
    decision = 'none'
    for note in GUEST_CLIENT.get_all_notes(forum=forum.id):
        if 'decision' in note.content.keys():
            decision = note.content['decision']
            break

    # e.g. If the paper was withdrawn
    if not review_notes:
        return ForumStatus.NO_REVIEWS, decision

    # Earliest creation time out of all the reviews. Changes made before this
    # cannot have been influenced by reviewers.
    first_review_time = min(rev.tcdate for rev in review_notes)

    # Retrieve all revisions of the manuscript
    references = sorted(GUEST_CLIENT.get_all_references(referent=forum.id,
                                                        original=True),
                        key=lambda x: x.tcdate)

    # The 'final' version is the latest version associated with a valid PDF
    final_reference, final_binary = get_last_valid_reference(references)

    # The 'initial' version is the last version associated with a valid PDF
    # that was created before the first review
    references_before_review = [
        r for r in references if r.tcdate <= first_review_time
    ]
    initial_reference, initial_binary = get_last_valid_reference(
        references_before_review)

    # Proceed only for forums with valid and distinct initial and final
    # versions
    if final_reference is not None and initial_reference is not None:
        if not final_reference.id == initial_reference.id:

            # Create subdirectory
            forum_dir = f'{output_dir}/{forum.id}'
            os.makedirs(forum_dir, exist_ok=False)

            # Write pdfs and metadata
            write_pdfs(forum_dir, initial_binary, final_binary)
            write_metadata(forum_dir, forum, conference, initial_reference.id,
                           final_reference.id, decision, review_notes)

            return ForumStatus.COMPLETE, decision
        else:
            # Manuscript was not revised after the first review
            return ForumStatus.NO_REVISION, decision
    else:
        # No versions associated with valid PDFs were found
        return ForumStatus.NO_PDF, decision


def main():

    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    statuses = []
    forum_notes = GUEST_CLIENT.get_all_notes(
        invitation=INVITATIONS[args.conference])
    for forum in tqdm.tqdm(forum_notes):
        status, decision = retrieve_forum(forum, args.conference, args.output_dir)
        statuses.append((forum.id, status, decision))

    with open(f'{args.status_file_prefix}{args.conference}.tsv', 'w') as f:
        f.write('#Conference\tForum\tStatus\tDecision\n')
        for forum, status, decision in statuses:
            f.write(f'{args.conference}\t{forum}\t{status}\t{decision}\n')


if __name__ == "__main__":
    main()
