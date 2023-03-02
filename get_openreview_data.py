"""
This script collects the following events from Open Review,
saves event metadata to tsv, and
saves paper revisions to pdf and Notes to json.
1. Paper revisions, picked according to tmdate since our retrieved contents were submitted at tmdate
  a) pre-rebuttal: the last submission revision before the review release or rebuttal starting time
  b) rebuttal: the last rebuttal revision before the rebuttal ending time
  c) final: the last revision which is assumed to be the camera ready version (some conferences
     do not have camera ready deadlines)
2. Comments from reviewers, authors, and metareviewers
  a) review revisions (with ratings), other comments from reviewers
  b) rebuttals, i.e. author comments,
  c) metareviews (with decisions), other comments from metareviewers

The following events are ignored
1. other paper revisions
2. comments from people other than authors, reviewers, and metareviewers

The output paths are
 - {args.output_dir} / metadata_{args.conference}*.tsv
 - {args.output_dir} / {args.conference} / {forum_id} / pre-rebuttal_revision.{pdf, json}
 - {args.output_dir} / {args.conference} / {forum_id} / rebuttal_revision.{pdf, json}
 - {args.output_dir} / {args.conference} / {forum_id} / final_revision.{pdf, json}
 - {args.output_dir} / {args.conference} / {forum_id} / comments / {comment_id}_{revision_index}.json
"""

import argparse
import collections
import csv
import hashlib
import json
import math
import os
import tqdm

import openreview
import openreview_lib as orl
import conference_lib as conflib

GUEST_CLIENT = openreview.Client(baseurl="https://api.openreview.net")

parser = argparse.ArgumentParser(description="")
parser.add_argument("-c", "--conference", type=str, choices=conflib.CONFERENCE_TO_INVITATION.keys(),
                    help="conference_year, e.g. iclr_2022")
parser.add_argument("-f", "--offset", default=0, type=int,
                    help="skip a number of submissions")
parser.add_argument("-b", "--batch_size", default=None, type=int,
                    help="if set, process just a small number of submissions to test this script")
parser.add_argument("-o", "--output_dir", default="data/", type=str,
                    help="output directory for metadata tsv, json, and pdf files")
parser.add_argument("--debug", action='store_true', help="only process one batch")


##### HELPERS #####
def make_path(directories, filename=None):
    directory = os.path.join(*directories)
    os.makedirs(directory, exist_ok=True)
    if filename is not None:
        return os.path.join(*directories, filename)

def write_note_json(note, json_path):
    with open(json_path, "w") as f:
        json.dump(note.to_json(), f)

def get_pdf_status(note, is_reference=True):
    try:  # try to get the PDF for this paper revision
        pdf_binary = GUEST_CLIENT.get_pdf(note.id, is_reference=is_reference)
        pdf_checksum = hashlib.md5(pdf_binary).hexdigest()
        pdf_status = orl.PDFStatus.AVAILABLE
    except openreview.OpenReviewException as e:
        pdf_status = orl.PDF_ERROR_STATUS_LOOKUP[e.args[0]["name"]]
        pdf_binary = "None"
        pdf_checksum = "None"
    return pdf_status, pdf_binary, pdf_checksum

def write_pdf(pdf_binary, pdf_path):
    assert pdf_binary != "None"
    with open(pdf_path, "wb") as f:
        f.write(pdf_binary)


##### PRODUCE DATA #####
def process_manuscript_revisions(forum_note, forum_idx, forum_dir, args):
    forum_id = forum_note.id
    original_id = forum_note.original

    # we care about the last revision in each of three stages
    revisions = {
        orl.EventType.PRE_REBUTTAL_REVISION: None,
        orl.EventType.REBUTTAL_REVISION: None,
        orl.EventType.FINAL_REVISION: None,
    }

    # loop over paper revisions to find three desired ones
    references = sorted(
        GUEST_CLIENT.get_all_references(referent=forum_id, original=True),
        key=lambda x: x.tmdate, # our retrieved contents are updated at tmdate
        reverse=True
    )
    for note in references:
        # In case the original submission note is unexpectedly returned as a reference to
        # the blind submission note, ignore it. This happens for ICLR 2018.
        if note.id == original_id:
            continue

        if note.tmdate <= conflib.CONFERENCE_TO_TIMES[args.conference]["review_notification"]:
            if (
                    revisions[orl.EventType.PRE_REBUTTAL_REVISION] is None or
                    revisions[orl.EventType.PRE_REBUTTAL_REVISION][0].tmdate < note.tmdate
            ):
                pdf_status, pdf_binary, pdf_checksum = get_pdf_status(note)
                if pdf_status == orl.PDFStatus.AVAILABLE:
                    revisions[orl.EventType.PRE_REBUTTAL_REVISION] = (note, pdf_status, pdf_binary, pdf_checksum)

        elif note.tmdate <= conflib.CONFERENCE_TO_TIMES[args.conference]["decision_notification"]:
            if (
                    revisions[orl.EventType.REBUTTAL_REVISION] is None or
                    revisions[orl.EventType.REBUTTAL_REVISION][0].tmdate < note.tmdate
            ):
                pdf_status, pdf_binary, pdf_checksum = get_pdf_status(note)
                if pdf_status == orl.PDFStatus.AVAILABLE:
                    revisions[orl.EventType.REBUTTAL_REVISION] = (note, pdf_status, pdf_binary, pdf_checksum)

        else: # note.tmdate > conflib.CONFERENCE_TO_TIMES[args.conference]["decision_notification"]
            if (
                    revisions[orl.EventType.FINAL_REVISION] is None or
                    revisions[orl.EventType.FINAL_REVISION][0].tmdate < note.tmdate
            ):
                pdf_status, pdf_binary, pdf_checksum = get_pdf_status(note)
                if pdf_status == orl.PDFStatus.AVAILABLE:
                    revisions[orl.EventType.FINAL_REVISION] = (note, pdf_status, pdf_binary, pdf_checksum)

    # the forum note has the same pdf as the last revision, which typically is our retrieved final_revision
    # pdf_status, pdf_binary, pdf_checksum = get_pdf_status(forum_note, is_reference=False)
    # if pdf_status == orl.PDFStatus.AVAILABLE:
    #     if revisions[orl.EventType.FINAL_REVISION] is not None:
    #         assert pdf_checksum == revisions[orl.EventType.FINAL_REVISION][-1]
    #     elif revisions[orl.EventType.REBUTTAL_REVISION] is not None:
    #         assert pdf_checksum == revisions[orl.EventType.REBUTTAL_REVISION][-1]
    #     else:
    #         assert pdf_checksum == revisions[orl.EventType.PRE_REBUTTAL_REVISION][-1]

    # create events and save files
    events = []
    for event_type in revisions:
        if revisions[event_type] is None:
            continue

        note, pdf_status, pdf_binary, pdf_checksum = revisions[event_type]

        assert note.referent == forum_id
        revision_index = orl.REVISION_TO_INDEX[event_type]
        assert note.replyto is None
        initiator, initiator_type = orl.get_initiator_and_type(note.signatures)
        assert initiator_type == orl.InitiatorType.CONFERENCE

        # save json
        json_path = make_path([forum_dir], f"{event_type}.json")
        write_note_json(note, json_path)
        # save pdf
        pdf_path = make_path([forum_dir], f"{event_type}.pdf")
        write_pdf(pdf_binary, pdf_path)

        # create an Event for this note
        events.append(orl.Event(
            # Identifiers
            forum_idx=forum_idx,
            forum_id=forum_id, # we don't use note.forum which may be None
            referent_id=forum_id,
            revision_index=revision_index,
            note_id=note.id,
            reply_to=note.replyto,
            # Event creator info
            initiator=initiator,
            initiator_type=initiator_type,
            # Date info
            creation_date=note.tcdate,
            mod_date=note.tmdate,
            # Event type info
            event_type=event_type,
            # File info
            json_path=json_path,
            pdf_status=pdf_status,
            pdf_path=pdf_path,
            pdf_checksum=pdf_checksum,
        ))

    return events


def process_comment(comment_note, forum_idx, forum_id, forum_comment_dir):
    events = []

    # classify the comment
    event_type = orl.get_comment_event_type(comment_note)

    # Official Review may have multiple revisions, others comments do not
    if event_type == orl.EventType.REVIEW:
        notes = [comment_note] + GUEST_CLIENT.get_all_references(referent=comment_note.id)
    else:
        # other comments don't have revisions, just save the comments notes
        notes = [comment_note]

    for revision_index, note in enumerate(notes):
        initiator, initiator_type = orl.get_initiator_and_type(note.signatures)

        # save json
        json_path = make_path([forum_comment_dir], f"{comment_note.id}_{revision_index}.json")
        write_note_json(note, json_path)

        # create an Event for this note
        events.append(orl.Event(
            # Identifiers
            forum_idx=forum_idx,
            forum_id=forum_id, # we don't use note.forum which may be None
            referent_id=note.referent if note.referent is not None else "None",
            revision_index=revision_index,
            note_id=note.id,
            reply_to=note.replyto,
            # Event creator info
            initiator=initiator,
            initiator_type=initiator_type,
            # Date info
            creation_date=note.tcdate,
            mod_date=note.tmdate,
            # Event type info
            event_type=event_type,
            # File info
            json_path=json_path,
            pdf_status=orl.PDFStatus.NOT_APPLICABLE,
            pdf_path="None",
            pdf_checksum="None",
        ))

    return events


def main():
    args = parser.parse_args()
    assert args.conference in conflib.CONFERENCE_TO_INVITATION
    print(conflib.CONFERENCE_TO_TIMES[args.conference])

    # Get all 'forum' notes (blind submission notes) from the conference; one forum note per paper
    forum_notes = sorted(
        GUEST_CLIENT.get_all_notes(invitation=conflib.CONFERENCE_TO_INVITATION[args.conference]),
        key=lambda x: x.tcdate,
    )[:100]

    if args.batch_size is None or args.batch_size <= 0:
        args.batch_size = len(forum_notes) - args.offset
        n_batches = 1
    else:
        n_batches = math.ceil((len(forum_notes) - args.offset) / args.batch_size)

    # loop over batches
    for i in tqdm.tqdm(range(n_batches)):
        events = []

        # loop over forums in this batch
        for j, forum_note in enumerate(tqdm.tqdm(
                forum_notes[args.offset + i * args.batch_size: args.offset + (i + 1) * args.batch_size]
        )):
            forum_idx = args.offset + i * args.batch_size + j
            forum_dir = os.path.join(
                args.output_dir, args.conference, forum_note.id
            )  # for {pre-rebuttal, rebuttal, final}_revision.{pdf, json}
            forum_comment_dir = os.path.join(
                forum_dir, "comments"
            )  # for {comment_id}_{revision_index}.json

            # three revisions: pre-rebuttal, rebuttal, final
            forum_events = process_manuscript_revisions(forum_note, forum_idx, forum_dir, args)

            # loop over comments in this forum
            for comment_note in sorted(
                    GUEST_CLIENT.get_all_notes(forum=forum_note.id),
                    key=lambda x: x.tcdate
            ):
                # skip the forum note
                if comment_note.id in [forum_note.id, forum_note.original]:
                    continue

                # process comments by authors, reviewers, metareviewers
                forum_events += process_comment(comment_note, forum_idx, forum_note.id, forum_comment_dir)

            # events += sorted(forum_events, key=lambda x: x.creation_date)
            events += forum_events

        # save metadata for forums in this batch
        if n_batches == 1:
            if args.offset == 0:
                tsv_path = f"{args.output_dir}/metadata_{args.conference}.tsv"
            else:
                tsv_path = f"{args.output_dir}/metadata_{args.conference}_offset{args.offset}.tsv"
        else:
            if args.offset == 0:
                tsv_path = f"{args.output_dir}/metadata_{args.conference}_{str(i).zfill(4)}.tsv"
            else:
                tsv_path = f"{args.output_dir}/metadata_{args.conference}_offset{args.offset}_{str(i).zfill(4)}.tsv"
        with open(tsv_path, "w") as f:
            writer = csv.DictWriter(f, fieldnames=orl.EVENT_FIELDS, delimiter="\t")
            writer.writeheader()
            for event in events:
                writer.writerow(event._asdict())

        if args.debug:
            exit()


if __name__ == "__main__":
    main()
