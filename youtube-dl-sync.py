import os, subprocess
from multiprocessing.pool import ThreadPool
from pytube import YouTube, Playlist, exceptions
import time

class PlaylistSync:
    def __init__(this, ytPlaylist, blacklist=[], threadCount=8):
        this.ytPlaylist = ytPlaylist
        this.ffmpegArgs = "-n"
        this.path = os.getcwd()
        this.blacklist = blacklist
        this.failed = []
        this.pool = ThreadPool(processes=threadCount)
        this.ytFormats = {"mp3": '251'}
        this.itagFormat = {'251': "webm"}

    def download_mp3_from_link(this, link):
        print("get stream")
        s = this.get_vid_stream(link, this.ytFormats['mp3'])
        this.download_pytube_stream(s, this.convert_tomp3)

    def download_pytube_stream(this, s, convert=None):
        stream = s["stream"]
        if (stream == None):
            return
        print("starting", s['title'])
        try:
            stream.download(filename=s['title'], output_path=this.path)
        except Exception as e:
            print(e)
            this.failed.append({"error":e, "s":s})
            return
        print("done downloading", s['title'])
        if (convert != None):
            print("     converting:")
            convert(s)
            print("     finished converting")

    def convert_tomp3(this, s, retrys = 3):
        stream = s["stream"]
        fName = stream.default_filename.split(".")[0]
        fName_id = fName + f"-{s['id']}"
        from_format = this.itagFormat[s['itag']]
        path = this.path
        msg = ""
        try: # subprocess.call(cmd, shell=True)
            cmd = f'ffmpeg -i "{path}/{fName}.{from_format}" -codec:a libmp3lame -qscale:a 0 {this.ffmpegArgs} "{path}/{fName_id}.mp3" && rm "{path}/{fName}.{from_format}"'
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, shell=True)
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                stderr = stderr.decode('utf-8', 'replace')
                msg = stderr.strip().split('\n')[-1]
                this.failed.append({"error":msg})
        except FileNotFoundError as err:
            if (retrys >= 0):
                time.sleep(2)
                this.convert_tomp3(s, retrys-1)
            else:
                this.failed.append({"error":str(err)+str(msg)})

    def get_youtube_playlist_vid_urls(this, yt_pl_url):
        p = Playlist(yt_pl_url)
        return p.video_urls

    def get_downloaded_vid_ids(this):
        downloaded_vid_names = os.listdir(this.path)
        vid_ids = list(filter(lambda x: x!=False, map(this.split_vid_name, downloaded_vid_names)))
        return list(map(lambda x: Playlist._video_url(f"/watch?v={x}"),vid_ids))

    def find_new_video_links(this):
        blacklist_urls = map(lambda x: Playlist._video_url(f"/watch?v={x}"), this.blacklist)
        downloaded = this.get_downloaded_vid_ids()
        to_download = this.get_youtube_playlist_vid_urls(this.ytPlaylist)
        new_links = set(to_download) - set(downloaded) - set(blacklist_urls)
        return new_links

    def get_vid_stream(this, link, itag, alterITag = '140'):
        itag = str(itag)
        ret = {"link": link, "stream": None, "itag": None, "yt": None, "id": None, "title": None, "type": "pytube-youtube"}
        try:
            yt = YouTube(link)
            ret["yt"] = yt
        except exceptions.VideoUnavailable as e:
            this.failed.append({"error":e, "link":link})
            return ret
        stream = yt.streams.get_by_itag(itag)
        if (stream == None):
            itag = alterITag
            stream = yt.streams.get_by_itag(itag)
            if (stream == None):
                this.failed.append({"error":"cannot find a stream", "link":link, "itags": f"primary= {itag}, secondary={alterITag}"})
        ret["stream"] = stream
        ret["itag"] = itag
        ret["id"] = yt.video_id
        ret["title"] = yt.title
        return ret

    def print_errors(this):
        print("errors = ")
        for i in range(len(this.failed)):
            x = this.failed[i]
            if (x.get('split') != None):
                print(f"number {i}      error is {x['error']}      spilt failed on {x['split']}       name = {x['name']}")
            elif (x.get('s') != None):
                print(f"number {i}      error is {x['error']}      download failed on {x['s']}")
            elif (x.get('link') != None):
                print(f"number {i}      error is {x['error']}      get stream failed on {x['link']}")
            else:
                print(f"number {i}      error is {x['error']} ")

    def download(this):
        try:
            new_links = this.find_new_video_links()
            this.pool.map(this.download_mp3_from_link, new_links)
            this.pool.close()
        except KeyboardInterrupt:
            print("\n\n Early Exit")
        finally:
            this.print_errors()

    def add_split_vid_name(this, a, b):
        v_s = f"{a}-{b}"
        if (len(v_s) == 11):
            return (True, v_s)
        return (False, v_s)

    def split_vid_name(this, name):
        try:
            v = name.split(".")[-2].split("-")
            if (len(v[-1]) == 11):
                return v[-1]
            elif (len(v[-1]) == 9): # soundcloud
                t, s = this.add_split_vid_name(v[-2], v[-1])
                if (t):
                    return s
                else:
                    # this.failed.append({"error":"soundcloud link", "name":name, "split":v})
                    return False
            else:
                t, s = this.add_split_vid_name(v[-2], v[-1])
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
                            this.failed.append({"error":"not size 11", "name":name, "split":v})
                            return False
        except IndexError as e:
            if (name == ".DS_Store"):
                return False
            else:
                this.failed.append({"error":e, "name":name, "split":v})
                return False


def main():
    blacklist = ['KPl9jmmt3Ps', 'rHzpkqpnGLQ', '9_Ql1EmrzZE', '8kuNwhfpwKM', 'cI7LdJeNOz4', 'O4Se-Q2VOOU']
    playlist_url = "https://www.youtube.com/playlist?list=PL6Pqa2e9AspE6lbr24yQpLWI1wVFY7o5H"
    sync = PlaylistSync(playlist_url, blacklist)
    sync.download()
    # link = "https://www.youtube.com/watch?v=9Xnqa1kMvWI" #tst link



if __name__ == '__main__':
    main()