import requests
from xar.xarfile import XarFile
import zlib
from io import BytesIO
from xml.etree import ElementTree


class PartialXarFile:
    FORMAT = ">4sHHQQI"

    @staticmethod
    def load_toc_remote(url: str):
        try:
            toc = 0
            toc_size = 0
            with requests.get(url, stream=True) as r:
                chunk_list = b''
                for hdr in r.iter_content(chunk_size=64):
                    if not toc and not toc_size:
                        toc, toc_size = XarFile.get_toc_shape(hdr)
                    chunk_list += hdr
                    if len(chunk_list) >= (toc_size + toc):
                        break
                print(f"have full toc ({toc_size}, fetched {len(chunk_list)})")

                # trim to the correct size
                chunk_list = chunk_list[toc:toc_size + toc]
                return zlib.decompress(chunk_list)
        except requests.exceptions.ConnectionError:
            return PartialXarFile.load_toc_remote(url)

    @staticmethod
    def get_package_file_remote(url: str, filename: str):
        toc = PartialXarFile.load_toc_remote(url)
        with BytesIO(toc) as stream:
            file = ElementTree.parse(stream).getroot().findall(f"toc/file/name[.='{filename}']/../data")
            if not file:
                raise ValueError(f"Cannot find file '{file}'")
            file = file[0]
            offset = int(file.find("offset").text)
            size = int(file.find("size").text)
            print(f"Size: {size} Offset: {offset}")
            end = offset + size
            headers = {"Range": f"bytes-{offset}-{end}"}
            with requests.get(url, headers=headers) as req:
                return req.content


if __name__ == "__main__":
    x = PartialXarFile.get_package_file_remote("http://localhost/HP_AutoSetup.pkg", "Scripts")

    with open("Scripts", "wb+") as fw:
        fw.write(x)

    x = XarFile("Scripts").get_file("Scripts")

    with open("Scripts2", "wb+") as fp:
        fp.write(x)

    import gzip

    c = gzip.open("Scripts2", "r")
    x = c.read()
    print(x)