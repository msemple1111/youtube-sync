import os
import re


mp4_playlist = "/Volumes/Movies/music/playlists/certi1"
mp3_playlist = "/Volumes/Movies/music/playlists/certi2"

mp3path = "/Volumes/Movies/music/dnbMP3"

failed = []

def split_vid_name(name):
    try:
        v = name.split(".")[-2].split("-")
        if (len(v[-1]) == 11):
            return v[-1]
        elif (len(v[-1]) == 9): # soundcloud
            t, s = add_split_vid_name(v[-2], v[-1])
            if (t):
                return s
            else:
                return s
        else:
            t, s = add_split_vid_name(v[-2], v[-1])
            if (t):
                return s
            else:
                v_s2 = f"{v[-3]}-{s}"
                if (len(v_s2) == 11):
                    return v_s2
                else:
                    v_s3 = f"{v[-4]}-{v_s2}"
                    if (len(v_s3) == 11):
                        return v_s3
                    else:
                        failed.append({"error":"not size 11", "name":name, "split":v})
                        return False
    except IndexError as e:
        if (name == ".DS_Store"):
            return False
        else:
            failed.append({"error":e, "name":name, "split":v})
            return False

def add_split_vid_name(a, b):
    v_s = f"{a}-{b}"
    if (len(v_s) == 11):
        return (True, v_s)
    return (False, v_s)


def get_downloaded_vids():
    downloaded_vid_names = os.listdir(mp4_playlist)
    vid_ids_all = list(map(split_vid_name, downloaded_vid_names))
    return list(zip(vid_ids_all, downloaded_vid_names))

def copy_vid_id(z):
    id, name = z
    name_split = name.split(".")
    name = "".join(name_split[:-1])
    name = safe_filename(name)
    cmd = f'cp "{mp3path}/{name}.mp3" "{mp3_playlist}/{name}.mp3"'
    os.system(cmd)


def safe_filename(s: str, max_length: int = 255) -> str:
    # Characters in range 0-31 (0x00-0x1F) are not allowed in ntfs filenames.
    ntfs_characters = [chr(i) for i in range(0, 31)]
    characters = [
        r'"',
        r"\#",
        r"\$",
        r"\%",
        r"'",
        r"\*",
        r"\,",
        r"\.",
        r"\/",
        r"\:",
        r'"',
        r"\;",
        r"\<",
        r"\>",
        r"\?",
        r"\\",
        r"\^",
        r"\|",
        r"\~",
        r"\\\\",
    ]
    pattern = "|".join(ntfs_characters + characters)
    regex = re.compile(pattern, re.UNICODE)
    filename = regex.sub("", s)
    return filename[:max_length].rsplit(" ", 0)[0]


def main():
    vids = get_downloaded_vids()
    for i in range(len(vids)):
        copy_vid_id(vids[i])

    print("failes")
    print(failed)

if __name__ == '__main__':
    main()
    # print(safe_filename("s.p.y dljknfdv .mp3"))
