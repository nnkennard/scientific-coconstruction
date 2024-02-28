# Possible things to add
# Extended review
# Extended rebuttal
# Better way of determining latest 'pre-review' version (before review release date instead of before review writing date)

# Things that must be added
# Database for details of all
# Any other metadata required?
import collections
import json
import openreview
import os
import time

Review = collections.namedtuple("Review",
                                "review_id sentences rating reviewer tcdate")

# A client is required for any OpenReview API actions
guest_client = openreview.Client(baseurl='https://api.openreview.net')


def process_reviews(forum_note):
    reviews = []
    rebuttals = []
    forum_notes = openreview.tools.iterget_notes(guest_client,
                                                 forum=forum_note.id)
    for note in forum_notes:
        if is_review(note):
            reviews.append(note.to_json())
            candidate_rebuttals = [
                maybe_rebuttal  # maybe sort these by date
                for maybe_rebuttal in forum_notes
                if maybe_rebuttal.replyto == note.id
            ]
            rebuttal_found = False
            for maybe_rebuttal in candidate_rebuttals:
                if maybe_rebuttal.signatures[0].endswith('Authors'):
                    rebuttals.append(maybe_rebuttal.to_json())
                    rebuttal_found = True
            if not rebuttal_found:
                rebuttals.append(None)

    # Earliest creation time out of all the reviews. Changes made before this
    # cannot have been influenced by reviewers.
    first_review_time = min(r['tcdate'] for r in reviews)

    return reviews, rebuttals, first_review_time


# == PDF processing helpers ====================================================


def write_pdfs(forum_dir, initial_binary, final_binary):
    for binary, version in [(initial_binary, INITIAL), (final_binary, FINAL)]:
        assert binary is not None
        with open(f'{forum_dir}/{version}.pdf', "wb") as f:
            f.write(binary)


def process_manuscript_versions(forum_note, first_review_time, output_dir):
    # Retrieve all revisions of the manuscript
    references = sorted(guest_client.get_all_references(referent=forum_note.id,
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
            forum_dir = f'{output_dir}/{forum_note.id}'
            os.makedirs(forum_dir, exist_ok=True)

            # Write pdfs and metadata
            write_pdfs(forum_dir, initial_binary, final_binary)
            #write_metadata(forum_dir, forum, conference, initial_reference.id,
            #               final_reference.id, decision, review_notes)

            return ForumStatus.COMPLETE
        else:
            # Manuscript was not revised after the first review
            return ForumStatus.NO_REVISION
    else:
        # No versions associated with valid PDFs were found
        return ForumStatus.NO_PDF


def retrieve_forum_metadata(forum_note):
    decision = get_decision(forum_note)


def write_forum_info(reviews, rebuttals, author_ids, metadata, output_dir):
    forum_dir = f'{output_dir}/{forum_note.id}'
    os.makedirs(forum_dir, exist_ok=True)
    with open(f'{output_dir}/{forum_note.id}/metadata.json', 'w') as f:
        json.dump(
            {
                "reviews": reviews,
                "rebuttals": rebuttals,
                "author_ids": author_ids,
                "metadata": metadata
            }, f)


def process_forum(forum_note):

    reviews, rebuttals, first_review_time = process_reviews(forum_note)
    process_manuscript_versions(forum_note, first_review_time, "iclr_2022/")
    author_ids = forum_note.content['authorids']
    metadata = retrieve_forum_metadata(
        forum_note)  # including decision, others?
    write_forum_info(reviews, rebuttals, author_ids, metadata, "iclr_2022/")
    #return status


for i, forum_note in enumerate(
        openreview.tools.iterget_notes(guest_client, invitation=INVITATION)):
    status = process_forum(forum_note)
    time.sleep(4)
