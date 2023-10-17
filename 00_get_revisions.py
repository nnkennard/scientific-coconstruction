import openreview
import scc_lib


GUEST_CLIENT = openreview.Client(baseurl="https://api.openreview.net")

def write_pdfs():
    pass


def retrieve_forum(forum, conference):
    write_pdfs(forum_dir, forum, scc_lib.DATES[conference])
    with open(f'{forum_dir}/metadata.json', 'w') as f:
        f.write(json.dump(get_metadata(forum, conference), indent=2))

def retrieve_conference(conference):
    for forum in guest_client.get_forums(scc_lib.INVITATIONS[conference]):
        retrieve_forum(forum, conference)
        

def main():

    for conference in scc_lib.Conference.ALL:
        retrieve_conference(conference)
    
    pass


if __name__ == "__main__":
    main()
