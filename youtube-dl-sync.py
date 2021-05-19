import os, subprocess
from multiprocessing.pool import ThreadPool
from multiprocessing import Pool
from pytube import YouTube, Playlist, exceptions, request
import time
import asyncio
from aiohttp import ClientSession, TCPConnector
# import concurrent


playlist_url = "https://www.youtube.com/playlist?list=PL6Pqa2e9AspE6lbr24yQpLWI1wVFY7o5H"


class PlaylistSync:
    def __init__(self, ytPlaylistUrl, blacklist=[], threadCount=8, downloadCount=4):
        self.ytPlaylistUrl = ytPlaylistUrl
        self._session = None
        self.threadCount = threadCount
        self.downloadCount = downloadCount
        self.path = os.getcwd()
        self.blacklist = blacklist
        self.failed = []
        self.ytFormats = {"mp3": '251'}
        self.itagFormat = {'251': "webm"}
        self.downloaded_links = self.get_downloaded_links()

    async def download_pytube_stream(self, s, convert=None):
        stream = s["stream"]
        if (stream == None):
            return
        print("downloading", s['title'])
        try:
            await stream.download(filename=s['title'], output_path=self.path)
        except Exception as e:
            print(e)
            self.failed.append({"error":e, "s":s})
            return
        print("done downloading", s['title'])
        if (convert != None):
            print("     converting:", s['title'])
            convert(s)
            print("     finished converting", s['title'])

    def unpack_stream(self, s):
        stream = s["stream"]
        fName = stream.default_filename.split(".")[0]
        fName_id = fName + f"-{s['id']}"
        from_format = self.itagFormat[s['itag']]
        path = self.path
        return (fName, fName_id, path, from_format)

    async def convert_tomp3_async(self, s, retrys = 3):
        stream = s["stream"]
        fName = stream.default_filename.split(".")[0]
        fName_id = fName + f"-{s['id']}"
        from_format = self.itagFormat[s['itag']]
        path = self.path
        msg = ""
        try: # subprocess.call(cmd, shell=True)
            cmd = f'ffmpeg -i "{path}/{fName}.{from_format}" -codec:a libmp3lame -qscale:a 0 {self.ffmpegArgs} "{path}/{fName_id}.mp3" && rm "{path}/{fName}.{from_format}"'
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await process.communicate()
            # await process.wait()
            if process.returncode != 0:
                stderr = stderr.decode('utf-8', 'replace')
                msg = stderr.strip().split('\n')[-1]
                self.failed.append({"error":msg})
        except FileNotFoundError as err:
            if (retrys >= 0):
                time.sleep(2)
                await self.convert_tomp3_async(s, retrys-1)
            else:
                self.failed.append({"error":str(err)+str(msg)})
        print("done Convert, moving")

    def get_downloaded_vid_ids(self):
        downloaded_vid_names = os.listdir(self.path)
        vid_ids = list(filter(lambda x: x!=False, map(self.split_vid_name, downloaded_vid_names)))
        return list(map(lambda x: Playlist._video_url(f"/watch?v={x}"),vid_ids))

    def get_downloaded_links(self):
        blacklist_urls = list(map(lambda x: Playlist._video_url(f"/watch?v={x}"), self.blacklist))
        downloaded = self.get_downloaded_vid_ids()
        return blacklist_urls + downloaded

    async def get_vid_stream(self, link, itag, alterITag = '140'):
        itag = str(itag)
        ret = {"link": link, "stream": None, "itag": None, "yt": None, "id": None, "title": None, "type": "pytube-youtube"}
        try:
            yt = YouTube(link, session=self._session)
            ret["yt"] = yt
        except exceptions.VideoUnavailable as e:
            self.failed.append({"error":e, "link":link})
            return ret
        stream = (await yt.streams).get_by_itag(itag)
        if (stream == None):
            itag = alterITag
            stream = (await yt.streams).get_by_itag(itag)
            if (stream == None):
                self.failed.append({"error":"cannot find a stream", "link":link, "itags": f"primary= {itag}, secondary={alterITag}"})
        ret["stream"] = stream
        ret["itag"] = itag
        ret["id"] = yt.video_id
        ret["title"] = await yt.title
        return ret

    def print_errors(self):
        print("errors = ")
        for i in range(len(self.failed)):
            x = self.failed[i]
            if (x.get('split') != None):
                print(f"number {i}      error is {x['error']}      spilt failed on {x['split']}       name = {x['name']}")
            elif (x.get('s') != None):
                print(f"number {i}      error is {x['error']}      download failed on {x['s']}")
            elif (x.get('link') != None):
                print(f"number {i}      error is {x['error']}      get stream failed on {x['link']}")
            else:
                print(f"number {i}      error is {x['error']} ")

    def add_split_vid_name(self, a, b):
        v_s = f"{a}-{b}"
        if (len(v_s) == 11):
            return (True, v_s)
        return (False, v_s)

    def split_vid_name(self, name):
        v = ""
        try:
            v = name.split(".")[-2].split("-")
            if (len(v[-1]) == 11):
                return v[-1]
            elif (len(v[-1]) == 9): # soundcloud
                t, s = self.add_split_vid_name(v[-2], v[-1])
                if (t):
                    return s
                else:
                    # self.failed.append({"error":"soundcloud link", "name":name, "split":v})
                    return False
            else:
                t, s = self.add_split_vid_name(v[-2], v[-1])
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
                            self.failed.append({"error":"not size 11", "name":name, "split":v})
                            return False
        except IndexError as e:
            if (name == ".DS_Store"):
                return False
            else:
                self.failed.append({"error":e, "name":name, "split":v})
                return False

    async def download_mp3_from_link(self, link):
        print("get stream")
        s = await self.get_vid_stream(link, self.ytFormats['mp3'])
        await self.download_pytube_stream(s, self.convert_tomp3)

    async def download_async(self, p = None, convert_func = None):
        queue = asyncio.Queue()
        self.converting_tasks = []
        pool = p if p != None else Pool(self.threadCount)
        async with ClientSession() as self._session:
            self.ytPlaylist = Playlist(self.ytPlaylistUrl, session=self._session)
            yt_producer = self.produce_yt_stream(queue)
            consumers = [self.consume_stream(queue, pool, convert_func) for _ in range(self.downloadCount)]
            await asyncio.gather(yt_producer, *consumers)
            await self._session.close()

    def download(self, convert_func = None):
        print("started, looking for songs:")
        try:
            pool = Pool(self.threadCount)
            loop = asyncio.get_event_loop()
            runloop = self.download_async(pool, convert_tomp3)
            loop.run_until_complete(runloop)
            lct = len(self.converting_tasks)
            if (lct > 0):
                print("Finished downloading,", lct, "songs to convert")
                for x in self.converting_tasks:
                    x.get()
            else:
                print("Finished downloading")
        except KeyboardInterrupt:
            print("\n\n Early Exit")
            loop.run_until_complete(asyncio.sleep(0.5))
        finally:
            pool.close()
            loop.run_until_complete(self._session.close())
            loop.run_until_complete(asyncio.sleep(1))
            # loop.close()
            self.print_errors()
        # finally:
            # pool.shutdown()
            # for task in asyncio.Task.all_tasks():
            #     task.cancel()
            
        
    async def produce_yt_stream(self, queue):
        async for link in self.ytPlaylist.video_urls():
            if link not in self.downloaded_links:
                stream = await self.get_vid_stream(link, self.ytFormats['mp3'])
                await queue.put(stream)
        for _ in range(self.downloadCount):
            await queue.put(None)

    async def consume_stream(self, queue, pool, convert_func = None):
        while True:
            stream = await queue.get()  # wait for an item from the producer
            if stream is None:
                break
            else:
                await self.download_pytube_stream(stream)
                if convert_func != None:
                    p_task = pool.apply_async(convert_func, args = (self.unpack_stream(stream), self.failed ))
                    self.converting_tasks.append(p_task)

def convert_tomp3(s, failed, retrys = 3):
    ffmpegArgs = "-n"
    print("start convert")
    fName, fName_id, path, from_format = s
    msg = ""
    try: # subprocess.call(cmd, shell=True)
        cmd = f'ffmpeg -i "{path}/{fName}.{from_format}" -codec:a libmp3lame -qscale:a 0 {ffmpegArgs} "{path}/{fName_id}.mp3" && rm "{path}/{fName}.{from_format}"'
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, shell=True)
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            stderr = stderr.decode('utf-8', 'replace')
            msg = stderr.strip().split('\n')[-1]
            failed.append({"error":msg})
    except FileNotFoundError as err:
        if (retrys >= 0):
            time.sleep(0.25)
            convert_tomp3(s, failed, retrys-1)
        else:
            failed.append({"error":str(err)+str(msg)})

def main():
    #blacklist = ['KPl9jmmt3Ps', 'rHzpkqpnGLQ', '9_Ql1EmrzZE', '8kuNwhfpwKM', 'cI7LdJeNOz4', 'O4Se-Q2VOOU']
    blacklist = []
    # playlist_url = "https://www.youtube.com/playlist?list=PLI2omNcnpT1OMrKugA6BAFh021kLo3QHA"

    sync = PlaylistSync(playlist_url, blacklist)
    sync.download(convert_tomp3)

    # link = "https://www.youtube.com/watch?v=9Xnqa1kMvWI" #tst link

if __name__ == '__main__':
    main()