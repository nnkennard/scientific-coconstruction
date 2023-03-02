from datetime import datetime as dt
import time, pytz


CONFERENCE_TO_INVITATION = {
    f"iclr_{year}": f"ICLR.cc/{year}/Conference/-/Blind_Submission"
    for year in range(2018, 2023)
}


def dt_to_unix(my_datetime):
    try:
        # naive datetime object (no time zone info), consider it a utc datetime
        return pytz.utc.localize(my_datetime).timestamp() * 1000
    except:
        # the datetime object already has time zone info
        return my_datetime.timestamp() * 1000


"""
We create datetime objects from UTC times, which we manually compute using 
times found from websites or with Open Review support.
The datetime objects are then converted to Unix timestamps (ms).
  
When there are multiple times for an occasion and we couldn't tell 
which is the most precise, we do the following.
1. review_release is used to get the last pre-rebuttal paper revision. We use the
EARLIEST candidate to avoid mistakenly retrieving a revision during rebuttal.
2. rebuttal_end is used to get the last rebuttal revision. We use the LATEST 
candidate to avoid missing a revision during rebuttal.
"""
CONFERENCE_TO_TIMES = {
    "iclr_2022": {
        "review_notification":   dt_to_unix(dt(2021, 11, 9, 6, 32, 0)),
        "decision_notification": dt_to_unix(dt(2022, 1, 20, 18, 35, 0)),
    },
}
for conf in CONFERENCE_TO_TIMES:
    assert CONFERENCE_TO_TIMES[conf]["review_notification"] < CONFERENCE_TO_TIMES[conf]["decision_notification"]