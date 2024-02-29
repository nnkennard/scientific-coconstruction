import argparse
import collections
import json
import openreview
import os
import time

import or_lib as orl
import pandas as pd

parser = argparse.ArgumentParser(description='')
parser.add_argument('-o',
                    '--output_dir',
                    type=str,
                    help='directory to write all pdfs and metadata',
                    required=True)
parser.add_argument('-r',
                    '--result_file',
                    type=str,
                    help='file to write results of the run',
                    required=True)

parser.add_argument('-d', '--debug', action='store_true', help='')

Review = collections.namedtuple("Review",
                                "review_id sentences rating reviewer tcdate")

# A client is required for any OpenReview API actions
guest_client = openreview.Client(baseurl='https://api.openreview.net')


def process_reviews(forum_notes):

    # Json-ified Note for each review
    reviews = []
    # Json-ified rebuttal for each review, or None if no rebuttal is found
    rebuttals = []

    # Currently, reviews and rebuttals consist of at most one note (does not
    # take into account comments that extend over replies or otherwise span
    # multiple notes)

    for note in forum_notes:
        # Conditions for an official review differ from year to year.
        if orl.is_review(note):
            reviews.append(note.to_json())
            # The earliest response to the review by the paper authors (if one
            # exists) is considered the rebuttal.
            candidate_rebuttals = [
                maybe_rebuttal for maybe_rebuttal in forum_notes
                if maybe_rebuttal.replyto == note.id
                and orl.is_by_authors(maybe_rebuttal)
            ]
            if candidate_rebuttals:
                rebuttals.append(
                    min(candidate_rebuttals, key=lambda x: x.tcdate).to_json())
            else:
                rebuttals.append(None)

    # Earliest creation time of all the reviews. Changes made before this
    # cannot have been influenced by reviewers.
    first_review_time = min(r['tcdate'] for r in reviews)

    return reviews, rebuttals, first_review_time


def write_pdfs(forum_dir, initial_binary, final_binary):
    for binary, version in [(initial_binary, orl.INITIAL),
                            (final_binary, orl.FINAL)]:
        assert binary is not None
        with open(f'{forum_dir}/{version}.pdf', "wb") as f:
            f.write(binary)


def process_manuscript_versions(forum_note, first_review_time, output_dir):
    # Retrieve all revisions of the manuscript
    references = sorted(guest_client.get_all_references(referent=forum_note.id,
                                                        original=True),
                        key=lambda x: x.tcdate)

    # The 'final' version is the latest version associated with a valid PDF
    final_reference, final_binary = orl.get_last_valid_reference(
        references, guest_client)

    # The 'initial' version is the last version associated with a valid PDF
    # that was created before the first review
    references_before_review = [
        r for r in references if r.tcdate <= first_review_time
    ]
    initial_reference, initial_binary = orl.get_last_valid_reference(
        references_before_review, guest_client)

    # Any issues with retrieving the pdf result in None, None being returned
    # above.

    # Proceed only for forums with valid and distinct initial and final
    # versions
    if final_reference is not None and initial_reference is not None:
        if final_reference.id == initial_reference.id:
            # Manuscript was not revised after the first review
            return orl.ForumStatus.NO_REVISION
        else:
            # Create subdirectory
            forum_dir = f'{output_dir}/{forum_note.id}'
            os.makedirs(forum_dir, exist_ok=True)

            # Write pdfs and metadata
            write_pdfs(forum_dir, initial_binary, final_binary)
            return orl.ForumStatus.COMPLETE
    else:
        # No versions associated with valid PDFs were found
        return orl.ForumStatus.NO_PDF


def retrieve_forum_metadata(forum_notes):
    forum_note = None
    for note in forum_notes:
        if note.id == note.forum:
            forum_note = note
    assert forum_note is not None
    return {
        'decision': orl.get_decision(forum_notes),
        'forum_id': forum_note.id,
        'author_ids': forum_note.content['authorids'],
    }


def prettify_json(reviews, rebuttals, metadata):
    """Clean up dumped json and new json to be readable."""
    return json.dumps(
        {
            "reviews": reviews,
            "rebuttals": rebuttals,
            "metadata": metadata
        },
        indent=2)


def write_forum_info(reviews, rebuttals, metadata, output_dir):
    forum_id = metadata['forum_id']
    forum_dir = f'{output_dir}/{forum_id}'
    # Dir should exist because PDFs were supposedly written
    assert os.path.isdir(forum_dir)
    with open(f'{forum_dir}/metadata.json', 'w') as f:
        f.write(prettify_json(reviews, rebuttals, metadata))


def process_forum(forum_note, output_dir):

    forum_notes = list(
        openreview.tools.iterget_notes(guest_client, forum=forum_note.id))

    # Collect reviews and rebuttals. The first review delimits the 'before'
    # period.
    reviews, rebuttals, first_review_time = process_reviews(forum_notes)

    # Extract the latest version before reviews, and the final version
    # available overall. This fn has side effects -- writes pdfs to output_dir.
    forum_status = process_manuscript_versions(forum_note, first_review_time,
                                               output_dir)

    if forum_status == orl.ForumStatus.COMPLETE:

        # Retrieve information such as accept/reject decision
        metadata = retrieve_forum_metadata(forum_notes)

        # Write all info output dir
        write_forum_info(reviews, rebuttals, metadata, output_dir)

    return forum_status


def main():
    args = parser.parse_args()

    statuses = []
    for i, forum_note in enumerate(
            openreview.tools.iterget_notes(guest_client,
                                           invitation=orl.INVITATION)):
        if args.debug and i == 100:
            break

        status = process_forum(forum_note, args.output_dir)
        statuses.append({"forum_id": forum_note.id, "status": status})
        time.sleep(4)

    pd.DataFrame.from_dict(statuses).to_csv(args.result_file)


if __name__ == "__main__":
    main()
