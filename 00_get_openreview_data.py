import argparse
import collections
import json
import math
import os
import tqdm

import openreview
import openreview_lib as orl
import conference_lib as conflib

GUEST_CLIENT = openreview.Client(baseurl="https://api.openreview.net")

parser = argparse.ArgumentParser(description="")
parser.add_argument(
    "-c",
    "--conference",
    type=str,
    choices=conflib.CONFERENCE_TO_INVITATION.keys(),
    help="conference_year, e.g. iclr_2022",
)
parser.add_argument(
    "-f", "--offset", default=0, type=int, help="skip a number of submissions"
)
parser.add_argument(
    "-b",
    "--batch_size",
    default=100,
    type=int,
)
parser.add_argument(
    "-d",
    "--data_dir",
    default="data/",
    type=str,
    help="output directory for metadata tsv, json, and pdf files",
)
parser.add_argument("--debug", action="store_true", help="only process one batch")

Revision = collections.namedtuple("Revision", "event_type path tmdate")

Review = collections.namedtuple(
    "Review", "review_id review_content reviewer tcdate tmdate"
)

Rebuttal = collections.namedtuple(
    "Rebuttal", "rebuttal_ids rebuttal_content tcdate tmdate"
)

ReviewRebuttalPair = collections.namedtuple("ReviewRebuttalPair", "review rebuttal")

Forum = collections.namedtuple(
    "Forum", "forum_id decision metareview_text review_rebuttal_pairs versions"
)


# === PDF HELPERS ===
def make_path(directories, filename=None):
    directory = os.path.join(*directories)
    if filename is not None:
        return os.path.join(*directories, filename)


def get_pdf_status(note, is_reference=True):
    try:  # try to get the PDF for this paper revision
        pdf_binary = GUEST_CLIENT.get_pdf(note.id, is_reference=is_reference)
        pdf_status = orl.PDFStatus.AVAILABLE
    except openreview.OpenReviewException as e:
        pdf_status = orl.PDF_ERROR_STATUS_LOOKUP[e.args[0]["name"]]
        pdf_binary = "None"
    return pdf_status, pdf_binary


def write_pdf(pdf_binary, pdf_path):
    assert pdf_binary != "None"
    with open(pdf_path, "wb") as f:
        f.write(pdf_binary)


def maybe_get_revision(note):
    if note is None:
        return None, None
    pdf_status, pdf_binary = get_pdf_status(note)
    if pdf_status == orl.PDFStatus.AVAILABLE:
        return pdf_binary, note.tmdate
    else:
        return None, None


# === PRODUCE DATA ===


def get_milestone_revisions(forum_note, conference, forum_dir):
    # we care about the last revision in each of three stages
    revisions = {
        orl.EventType.PRE_REBUTTAL_REVISION: None,
        orl.EventType.REBUTTAL_REVISION: None,
        orl.EventType.FINAL_REVISION: None,
    }

    # loop over paper revisions to find three desired ones
    references = sorted(
        GUEST_CLIENT.get_all_references(referent=forum_note.id, original=True),
        key=lambda x: x.tmdate,  # our retrieved contents are updated at tmdate
    )

    previous_note = None
    review_notification_time = conflib.CONFERENCE_TO_TIMES[conference][
        "review_notification"
    ]
    decision_notification_time = conflib.CONFERENCE_TO_TIMES[conference][
        "decision_notification"
    ]

    # for note in references:
    #    print_timestamp(note.tmdate)

    for note in references:
        if note.id == forum_note.original:
            continue
        else:
            if (
                note.tmdate > review_notification_time
                and revisions[orl.EventType.PRE_REBUTTAL_REVISION] is None
            ):
                # Current note is the first AFTER review notification -- previous is the pre-rebuttal revision
                revisions[orl.EventType.PRE_REBUTTAL_REVISION] = maybe_get_revision(
                    previous_note
                )
            if (
                note.tmdate > decision_notification_time
                and revisions[orl.EventType.REBUTTAL_REVISION] is None
            ):
                # Current note is the first AFTER decision notification -- previous is the rebuttal revision
                revisions[orl.EventType.REBUTTAL_REVISION] = maybe_get_revision(
                    previous_note
                )
                break
            previous_note = note
    # the last valid note is the final revision
    for note in reversed(references):
        if revisions[orl.EventType.FINAL_REVISION] in [None, (None, None)]:
            revisions[orl.EventType.FINAL_REVISION] = maybe_get_revision(note)
        else:
            break

    for milestone, maybe_revision in revisions.items():
        # print(milestone, end=" ")
        flag = False
        if maybe_revision is not None:
            pdf_binary, x = maybe_revision
            # print_timestamp(x)
            flag = True
            if pdf_binary is not None:
                write_pdf(pdf_binary, make_path([forum_dir], f"{milestone}.pdf"))
        if not flag:
            print(None)

    # print("=" * 80)
    return sorted(revisions.items())


def process_manuscript_revisions(forum_note, forum_dir, conference):
    revisions = get_milestone_revisions(forum_note, conference, forum_dir)

    # create events and save files
    events = []
    for event_type, maybe_revision in revisions:
        if maybe_revision is not None:
            pdf_binary, revision_tmdate = maybe_revision
            if pdf_binary is not None:
                pdf_path = make_path([forum_dir], f"{event_type}.pdf")
                write_pdf(pdf_binary, pdf_path)
                events.append(Revision(event_type, pdf_path, revision_tmdate))
            else:
                events.append(Revision(event_type, None, None))

        else:
            events.append(Revision(event_type, None, None))
    return events


# Review helpers


def export_signature(note):
    (signature,) = note.signatures
    return signature.split("/")[-1]


def get_replies(note, discussion_notes):
    return [x for x in discussion_notes if x.replyto == note.id]


def get_longest_thread(top_note, discussion_notes):
    threads = [[top_note]]
    while True:
        new_threads = []
        for thread in threads:
            thread_last = thread[-1]
            candidates = [
                c
                for c in get_replies(thread_last, discussion_notes)
                if c.signatures == thread_last.signatures
            ]
            for candidate in candidates:
                new_threads.append(thread + [candidate])
        if not new_threads:
            break
        threads = new_threads
    return max(threads, key=lambda x: len(x))


def get_rebuttal_thread(review_note, forum_notes):
    possible_rebuttal_starts = [
        n
        for n in forum_notes
        if n.replyto == review_note.id and "Authors" in n.signatures[0]
    ]
    if not possible_rebuttal_starts:
        return []
    longest_rebuttal_threads = [
        get_longest_thread(p, forum_notes) for p in possible_rebuttal_starts
    ]

    return sorted(longest_rebuttal_threads, key=lambda x: (-len(x), x[0].tcdate))[0]


def get_reviews(forum_notes):
    review_notes = []
    rebuttal_threads = []
    for note in forum_notes:
        if note.replyto == note.forum:
            if (
                "main_review" in note.content
                or "review" in note.content  # 2022  # 2020
            ):
                review_notes.append(note)  # 2022 does not have weird threads
                rebuttal_threads.append(get_rebuttal_thread(note, forum_notes))

    if not review_notes:
        return []

    review_rebuttal_pairs = []
    for review_note, rebuttal_thread in zip(review_notes, rebuttal_threads):
        review_rebuttal_pairs.append(
            ReviewRebuttalPair(
                Review(
                    review_note.id,
                    json.dumps(review_note.content),
                    export_signature(review_note),
                    review_note.tcdate,
                    review_note.tmdate,
                ),
                Rebuttal(
                    [n.id for n in rebuttal_thread],
                    [json.dumps(n.content) for n in rebuttal_thread],
                    min(n.tcdate for n in rebuttal_thread) if rebuttal_thread else None,
                    max(n.tmdate for n in rebuttal_thread) if rebuttal_thread else None,
                ),
            )
        )
    return review_rebuttal_pairs


def get_metareview(forum_notes):
    for note in forum_notes:
        if "decision" in note.content and "comment" in note.content:
            return note.content["decision"], note.content["comment"]

    assert False


def process_forum(forum_note, forum_dir, conference):
    # three revisions: pre-rebuttal, rebuttal, final

    revisions = process_manuscript_revisions(forum_note, forum_dir, conference)
    forum_notes = sorted(
        GUEST_CLIENT.get_all_notes(forum=forum_note.id), key=lambda x: x.tcdate
    )
    review_rebuttal_pairs = get_reviews(forum_notes)

    assert forum_note.id is not None
    decision, metareview_text = get_metareview(forum_notes)

    with open(f"{forum_dir}/discussion.json", "w") as f:
        json.dump(
            jsonify_forum(
                Forum(
                    forum_note.id,
                    decision,
                    metareview_text,
                    review_rebuttal_pairs,
                    revisions,
                )
            ),
            f,
        )


def jsonify_forum(forum):
    forum_dict = forum._asdict()
    forum_dict["review_rebuttal_pairs"] = [
        {"review": p.review._asdict(), "rebuttal": p.rebuttal._asdict()}
        for p in forum_dict["review_rebuttal_pairs"]
    ]
    return forum_dict


def get_batch_size(batch_size, forum_notes):
    if batch_size is None or batch_size <= 0:
        return len(forum_notes)
    else:
        return batch_size


def main():
    args = parser.parse_args()
    assert args.conference in conflib.CONFERENCE_TO_INVITATION

    # Get all 'forum' notes (blind submission notes) from the conference; one forum note per paper
    conference_notes = sorted(
        GUEST_CLIENT.get_all_notes(
            invitation=conflib.CONFERENCE_TO_INVITATION[args.conference]
        ),
        key=lambda x: x.tcdate,
    )[args.offset :]

    # This is all very tedious but required because of processes sometimes getting killed
    batch_size = get_batch_size(args.batch_size, conference_notes)
    n_batches = math.ceil(len(conference_notes) / batch_size)

    # loop over batches
    for i in tqdm.tqdm(range(n_batches)):
        # loop over forums in this batch
        batch_start = args.offset + i * batch_size
        batch_end = batch_start + batch_size
        for forum_note in tqdm.tqdm(conference_notes[batch_start:batch_end]):
            forum_dir = os.path.join(
                args.data_dir, args.conference, forum_note.id
            )  # for {pre-rebuttal, rebuttal, final}_revision.{pdf, json}

            os.makedirs(forum_dir, exist_ok=True)

            process_forum(forum_note, forum_dir, args.conference)
        if args.debug:
            break


if __name__ == "__main__":
    main()
