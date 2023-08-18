import os
import struct
import zlib
from io import BytesIO
from xml.etree import ElementTree


class XarFile:
    FORMAT = ">4sHHQQI"

    def __init__(self, file: str):
        self.file = file
        with open(file, "rb") as fp:
            self.toc, self.toc_size = self.get_toc_shape(fp.read(64))
            print(f"TOC size: {self.toc_size} TOC start: {self.toc}")
            fp.seek(self.toc, os.SEEK_SET)
            self.table = zlib.decompress(fp.read(self.toc_size))

    def list_files(self):
        with BytesIO(self.table) as stream:
            root = ElementTree.parse(stream).getroot()
            for f in (ele.find("name").text for ele in root.findall("toc/file")):
                print(f)

    def get_file(self, filename: str):
        with BytesIO(self.table) as stream:
            root = ElementTree.parse(stream).getroot()
            file = root.findall(f"toc/file/name[.='{filename}']/../data")
            if not file:
                raise ValueError(f"Cannot find file '{filename}'")
            file = file[0]
            offset = int(file.find("offset").text) + self.toc + self.toc_size
            size = int(file.find("size").text)

            print(f"Reading {size} bytes from {offset}")

            with open(self.file, "rb") as fp:
                fp.seek(offset, os.SEEK_SET)
                return fp.read(size)

    @staticmethod
    def get_toc_shape(header: bytes):
        """Calculate the size of the TOC and the start offset"""
        """Returns a tuple of (start offset, compressed size)"""

        if len(header) < 64:
            raise ValueError(f"Need at least 64 bytes of header to calculate")

        # discard checksum
        magic, header_size, version, toc_compressed, toc_uncompressed, _ = \
            struct.unpack(XarFile.FORMAT, header[:struct.calcsize(XarFile.FORMAT)])

        if magic != b"xar!":
            raise ValueError(f"Incorrect magic: {magic}")

        if version != 1:
            raise ValueError(f"Unknown version: {version.decode()}")

        if header_size != 28:
            raise ValueError(f"Unknown header size: {header_size.decode()}")

        # XAR archive, version: 1, header size: 28, TOC compressed: 4207, TOC uncompressed: 13817, checksum: SHA1
        print(f"XAR archive, version: {version}, header size: {header_size}, TOC compressed: {toc_compressed},"
              f" TOC uncompressed: {toc_uncompressed}")

        # there is either 0, 4, or 36 bytes of padding, we need to find out how much
        # in order to locate the start of the TOC
        padding_size = 0
        if header[28:] == b'\x00' * 36:
            padding_size = 36
        elif header[28:32] == b'\x00' * 4:
            padding_size = 4
        elif header[28] != b'\x00':
            pass

        # we now where the TOC starts
        return (struct.calcsize(XarFile.FORMAT) + padding_size), toc_compressed
