class Conference(object):
    iclr_2018 = "iclr_2018"
    iclr_2019 = "iclr_2019"
    iclr_2020 = "iclr_2020"
    iclr_2021 = "iclr_2021"
    iclr_2022 = "iclr_2022"
    ALL = [iclr_2018, iclr_2019, iclr_2020, iclr_2021, iclr_2022]

INVITATIONS = {
    f"iclr_{year}": f"ICLR.cc/{year}/Conference/-/Blind_Submission"
        for year in range(2018, 2023)
        }
