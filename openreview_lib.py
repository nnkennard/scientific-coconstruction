import collections


EVENT_FIELDS = [
    # Identifiers
    "forum_idx",
    "forum_id",
    "referent_id",
    "revision_index",   # 0 indicates the referent, 1 is the first actual revision
    "note_id",
    "reply_to",         # 'replyto' from OpenReview
    # Event creator info
    "initiator",        # from 'signatures' from OpenReview
    "initiator_type",   # one of the InitiatorType strings
    # Date info
    "creation_date",    # 'true creation date' from OpenReview
    "mod_date",         # 'true modification date' from OpenReview
    # Event type info
    "event_type",       # see below
    # File info
    "json_path",
    "pdf_status",
    "pdf_path",         # None for comments
    "pdf_checksum",     # None for comments
]
Event = collections.namedtuple("Event", EVENT_FIELDS)


# A unified set of initiator types shared by all venues
# We ignore events' initiated by public readers
class InitiatorType(object):
    CONFERENCE      = "conference"
    AUTHOR          = "author"
    REVIEWER        = "reviewer"
    METAREVIEWER    = "metareviewer"
    OTHER           = "other"

# Map conference-specific initiator types to our unified set of initiator types.
# See notebooks in the explore_conferences directory for conference-specific initiator types.
def get_initiator_and_type(signatures):
    initiators = [s.split("/")[-1] for s in signatures]
    combined_initiators = "|".join(initiators)

    initiator = initiators[0].split("/")[-1]
    if "Conference" in initiator:
        return combined_initiators, InitiatorType.CONFERENCE
    elif "Authors" == initiator:
        return combined_initiators, InitiatorType.AUTHOR
    elif "Reviewer" in initiator:
        return combined_initiators, InitiatorType.REVIEWER
    elif "Chair" in initiator:
        return combined_initiators, InitiatorType.METAREVIEWER
    else:
        return combined_initiators, InitiatorType.OTHER


# A unified set of event types shared by all venues
class EventType(object):
    # paper
    PRE_REBUTTAL_REVISION   = "pre-rebuttal_revision"
    REBUTTAL_REVISION       = "rebuttal_revision"
    FINAL_REVISION          = "final_revision"
    # comments
    REVIEW              = "review"  # Official_Review which may have multiple revisions
    METAREVIEW          = "metareview"
    COMMENT             = "comment" # other official comments, with various initiator_type
    PUBLIC_COMMENT      = "public_comment" # comments from public readers

REVISION_TO_INDEX = {
    EventType.PRE_REBUTTAL_REVISION:    0,
    EventType.REBUTTAL_REVISION:        1,
    EventType.FINAL_REVISION:           2,
}

# Map conference-specific comment event types to our unified set of event types.
# This function handles comment notes, but not paper revisions.
# See notebooks in the explore_conferences directory for conference-specific event types.
def get_comment_event_type(note):
    if "Official_Review" in note.invitation:
        return EventType.REVIEW
    elif "Decision" in note.invitation:
        return EventType.METAREVIEW
    elif "Official_Comment" in note.invitation:
        return EventType.COMMENT
    elif "Public_Comment" in note.invitation:
        return EventType.PUBLIC_COMMENT
    else:
        raise ValueError("Unknown comment event type")


class PDFStatus(object):
    # for paper revisions
    AVAILABLE       = "available"
    DUPLICATE       = "duplicate"
    FORBIDDEN       = "forbidden"
    NOT_FOUND       = "not_found"
    # for comments
    NOT_APPLICABLE  = "not_applicable"

PDF_ERROR_STATUS_LOOKUP = {
    "ForbiddenError"    : PDFStatus.FORBIDDEN,
    "NotFoundError"     : PDFStatus.NOT_FOUND,
}