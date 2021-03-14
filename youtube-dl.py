from pytube import YouTube, Playlist, exceptions
from multiprocessing import Pool
from multiprocessing.pool import ThreadPool
import os
from random import randint
from youtube_dl import YoutubeDL
import asyncio
import subprocess


itags = ['251', '140']

# test_video_links = ["https://www.youtube.com/watch?v=u1YafBfRZCg", "https://www.youtube.com/watch?v=Z7otH2Wy7gg", "https://www.youtube.com/watch?v=debN7Y7Q_C4"]
path = os.getcwd()
# path = "/Volumes/Movies/music/dnbMP3"

dnb = "https://www.youtube.com/playlist?list=PL6Pqa2e9AspE6lbr24yQpLWI1wVFY7o5H"

playlist = dnb

ffmpegArgs = "-n"

# iTimes = randint(0, 25)
# iplus = randint(0, 740)

failed = []


def add_split_vid_name(a, b):
    v_s = f"{a}-{b}"
    if (len(v_s) == 11):
        return (True, v_s)
    return (False, v_s)

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
                failed.append({"error":"soundcloud link", "name":name, "split":v})
                return False
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




def get_downloaded_vid_ids():
    downloaded_vid_names = os.listdir(path)
    vid_ids = list(filter(lambda x: x!=False, map(split_vid_name, downloaded_vid_names)))
    return list(map(lambda x: Playlist._video_url(f"/watch?v={x}"),vid_ids))
    # print(vid_ids)
    # print("len=",len(vid_ids))
    # return vid_ids
    # for path, subdirs, files in os.listdir(r'/Volumes/Movies/music/dnb\ :\ jungle'):
    #     for filename in files:
    #         f = os.path.join(path, filename)
    #         a.write(str(f) + os.linesep)


def get_vid_streams(link):
    yt = YouTube(link)
    # yt.video_id
    return [(yt.streams.get_by_itag(i), i, yt.title, link) for i in itags]

def get_vid_stream(link, i):
    try:
        yt = YouTube(link)
    except exceptions.VideoUnavailable as e:
        failed.append({"error":e, "link":link})
        return (None, None, None, None, None)
    newI = str(i)
    stream = yt.streams.get_by_itag(i)
    if (stream == None):
        stream = yt.streams.get_by_itag('140')
        newI = '140'
        if (stream == None):
            failed.append({"error":"cannot find a stream", "link":link})
    return (stream, newI, yt.title, link, yt.video_id)

def checkIfDownloaded(vid_url, downloaded_id):
    d_url = p._video_url(f"/watch?v={downloaded_id}")
    return (vid_url == d_url)

def get_playlist_urls():
    p = Playlist(playlist)
    return p.video_urls

blacklist = ['KPl9jmmt3Ps', 'rHzpkqpnGLQ', '9_Ql1EmrzZE', '8kuNwhfpwKM', 'cI7LdJeNOz4', 'O4Se-Q2VOOU']
def find_new_video_links(pool):
    blacklist_urls = set(map(lambda x: Playlist._video_url(f"/watch?v={x}"), blacklist))
    [to_download, downloaded] = pool.map(lambda x: set(x()), [get_playlist_urls, get_downloaded_vid_ids])
    new_links = to_download - downloaded - blacklist_urls
    # new_streams = pool.map(get_vid_stream, new_links)
    return new_links

def download_mp4_from_link(link):
    print("starting",link)
    ydl = YoutubeDL({'format': '140'})
    ydl.download([link])
    print("done downloading", link)


def download_mp3_from_link(link):
    print("get stream")
    s = get_vid_stream(link, '251')
    download_stream(s)

def download_stream(s):
    (stream, i, title, link, id) = s
    if (stream == None):
        return
    elif (i == '140'):
        download_mp4_from_link(link)
        fName = title
    else:
        print("starting",title)
    newFName = stream.default_filename.split(".")[0] + f"-{id}"
    oFName = stream.default_filename.split(".")[0]
    # newI = abs((int(i)*(-iTimes)+iplus))
    # fName = title + str(newI)
    # if (i=='251'):
    #     fname = oFName+'.webm'
    # elif (i == '140'):
    #     fname = oFName+'.mp4'
    try:
        if (i!='140'): # mp4 format
            stream.download(filename=title, output_path=path)
    except Exception as e:
        print(e)
        failed.append({"error":e, "s":s})
        return

    print("done downloading", title)

    if (i=='251'): # webm format
        print("converting", title)
        # newFName = stream.default_filename.split(".")[0] + str(newI+iplus)
        # oFName = stream.default_filename.split(".")[0] + str(newI)

        # os.system(f'ffmpeg -i "{path}/{oFName}.webm" -c:a libfdk_aac -vbr 5 -cutoff 18000 "{path}/{newFName}.mp4"')
        # subprocess.call(f'ffmpeg -i "{path}/{oFName}.webm" -codec:a libmp3lame -qscale:a 0 {ffmpegArgs} "{path}/{newFName}.mp3"', shell=True)
        # os.system(f'rm "{path}/{oFName}.webm"')
        convert_tomp3('webm', newFName, oFName)
    if (i=='140'):
        # newFName = stream.default_filename.split(".")[0] + f"-{id}"
        oFName = f"{oFName}-{id}"
        # subprocess.call(f'ffmpeg -i "{path}/{oFName}.m4a" -codec:a libmp3lame -qscale:a 0 {ffmpegArgs} "{path}/{newFName}.mp3"', shell=True)
        # os.system(f'rm "{path}/{oFName}.m4a"')
        convert_tomp3('m4a', newFName, oFName)


def convert_tomp3(from_format, newFName, oFName):
    subprocess.call(f'ffmpeg -i "{path}/{oFName}.{from_format}" -codec:a libmp3lame -qscale:a 0 {ffmpegArgs} "{path}/{newFName}.mp3"', shell=True)
    os.system(f'rm "{path}/{oFName}.{from_format}"')


def main():
    pool = ThreadPool(processes=8)
    print("finding new vids")
    new_links = find_new_video_links(pool)
    print(f"got {len(new_links)} new video links, downloading now")
    # pool.map(download_mp3_from_link, new_links)
    print("done")
    pool.close()
    print("bye!")

def print_errors():
    print("errors = ")
    for i in range(len(failed)):
        x = failed[i]
        if (x.get('split') != None):
            print(f"number {i}      error is {x['error']}      spilt failed on {x['split']}       name = {x['name']}")
        if (x.get('s') != None):
            print(f"number {i}      error is {x['error']}      download failed on {x['s']}")
        if (x.get('link') != None):
            print(f"number {i}      error is {x['error']}      get stream failed on {x['link']}")
if __name__ == '__main__':
    try:
        main()
        print_errors()
    except KeyboardInterrupt:
        print("\n\n Early Exit")
        print_errors()





# ffmpeg -i "/Users/Michael/Music/dnb/Marcus Visionary - Real Warrior (L-Side Remix)3343.webm" -c:a libfdk_aac -vbr 5 -cutoff 18000 "/Users/Michael/Music/dnb/Marcus Visionary - Real Warrior (L-Side Remix)3343.m4a"

# vid_streams = [get_vid_streams(link) for link in video_links]

# streams = [stream for vid in vid_streams for stream in vid]

# [download_video(yt) for yt in videos]

# print("\n\n\n\nitimememmee00010101010101949875111"+str(iTimes)+ "76545678" )
# print("iplusssesemmee0001010137643875111"+str(iplus)+ "8335654" )


# yt.get_by_itag()

# sts = yt.streams.filter(only_audio=True)
