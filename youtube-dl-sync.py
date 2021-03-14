
class PlaylistSync:
    def PlaylistSync(platlist, blacklist=[]):
        this.playlist = platlist
        this.ffmpegArgs = "-n"
        this.path = os.getcwd()
        this.blacklist = blacklist

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

    def find_new_video_links(pool):
        blacklist_urls = set(map(lambda x: Playlist._video_url(f"/watch?v={x}"), blacklist))
        [to_download, downloaded] = pool.map(lambda x: set(x()), [get_playlist_urls, get_downloaded_vid_ids])
        new_links = to_download - downloaded - blacklist_urls
        # new_streams = pool.map(get_vid_stream, new_links)
        return new_links


def main():
    blacklist = ['KPl9jmmt3Ps', 'rHzpkqpnGLQ', '9_Ql1EmrzZE', '8kuNwhfpwKM', 'cI7LdJeNOz4', 'O4Se-Q2VOOU']
    playlist_url = "https://www.youtube.com/playlist?list=PL6Pqa2e9AspE6lbr24yQpLWI1wVFY7o5H"
    sync = PlaylistSync(playlist_url, blacklist)
