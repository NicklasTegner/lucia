# Copyright (C) 2018  LuciaSoftware and it's contributors.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see https://github.com/LuciaSoftware/lucia/blob/master/LICENSE.

"""Lucia's resource pack module

This module will aid in the interaction with and creation of data files for storing game assets.
A lucia resource file is a binary file format with the ability to have encryption and/or compression instituted on a per-file basis at creation time. Using the get method one may retrieve the contents of any file added to the pack, for example to be used in a memory load function of a sound system.
"""

import sys, os, struct
from . import data


class InvalidPackHeader(Exception):
	"""raised when the packs header is invalid"""

	pass


class ResourceFileVersion:
	"""The version should only change if changes are introduced that breaks backwards compatibility"""

	v1 = 1


class ResourceFileItem(object):
	"""Internal object representing an item in the pack."""

	def __init__(self, name, content, compress, encrypt):
		self.name = name
		self.content = content
		self.compress = compress
		self.encrypt = encrypt


class ResourceFile:
	"""The resource file object
	
	You will interact with resource files through methods provided by this object. This object may have any number of instances, however only one instance should interact with a given file on the file system at a time.
	"""

	def __init__(self, key, header=b"LURF", version=ResourceFileVersion.v1):
		"""Instantiates a resource container.
		
		args:
		    :param key: The encryption key to be used in this resource file.
		    :param header (bytes, optional): The header to be used to designate this resource file. Defaults to b'LURF'
		    :param version (ResourceFileVersion, optional): The version number to be written after the header. Defaults to V1, DO NOT CHANGE THIS UNLESS YOU KNOW WHAT YOU'RE DOING.
		"""
		self.key = key
		self.header = header
		self.header_length = len(self.header)
		self.version = version
		self.files = {}

	def load(self, filename):
		"""Opens a resource file to be read.
		
		This file will be checked for validity based on matching header, version, and a non-0 number of files. If one of these conditions fails, InvalidPackHeader will be raised. Otherwise this object will be loaded with the contents.
		    :param filename: The file name to be read from the file system.
		"""
		f = open(filename, "rb")
		test_header = f.read(self.header_length)
		test_header = struct.unpack(str(self.header_length) + "s", test_header)[0]
		test_version = f.read(4)
		test_version = struct.unpack("1i", test_version)[0]
		amount_of_files = f.read(4)
		amount_of_files = struct.unpack("1i", amount_of_files)[0]
		if test_header != self.header:
			raise InvalidPackHeader
		if test_version != self.version:
			raise InvalidPackHeader
		if amount_of_files == 0:
			raise InvalidPackHeader
		# Header and version is good, nice. Now resolve files.
		for x in range(0, amount_of_files):
			name_length = struct.unpack("1i", f.read(4))[0]
			name = f.read(name_length)
			content_length = struct.unpack("1i", f.read(4))[0]
			content_state = struct.unpack("2i", f.read(8))
			content = f.read(content_length)
			# if pack file specifies, decrypt/decompress the content.
			if content_state[1]:
				content = data.decrypt(content, self.key)
			if content_state[0]:
				content = data.decompress(content)
			# create an item for this file
			item = ResourceFileItem(name, content, content_state[0], content_state[1])
			self.files[name] = item

	def save(self, filename):
		"""Saves data added to this object to a resource file.
		
		When creating a resource file, this is the final method you would call.
		args:
		    :param filename: The file name on disk to write to. Will be overwritten if already exists.
		"""
		f = open(filename, "wb")
		# first write header
		f.write(struct.pack(str(self.header_length) + "s", self.header))
		# then write the version byte
		f.write(struct.pack("1i", self.version))
		# Write how many files are in the pack
		f.write(struct.pack("1i", len(self.files)))
		# and then loop through all files, and add them to the pack.
		for item in self.files.values():
			f.write(struct.pack("1i", len(item.name)))
			f.write(item.name)
			content = item.content
			if item.compress:
				content = data.compress(item.content)
			if item.encrypt:
				content = data.encrypt(content, self.key)
			f.write(struct.pack("1i", len(content)))
			f.write(struct.pack("2i", item.compress, item.encrypt))
			f.write(content)
		# and then close
		f.close()

	def add_file(self, name, compress=True, encrypt=True, internalname=None):
		"""Adds a file on disk to the pack, optionally compressing and/or encrypting it.
		
		args:
		    :param name: The file name to read from.
		    :param compress (boolean, optional): Whether compression should be applied to this file. Defaults to True.
		    :param encrypt (boolean, optional): Whether encryption should be applied to this file. Defaults to True.
		    :param internalname (optional): Internal file name to be used inside the pack. If None, the default, internal name will be same as name on disk.
		"""
		if os.path.exists(name) == False:
			raise FileNotFoundError
		f = open(name, "rb")
		content = f.read()
		f.close()
		if internalname is not None:
			name = internalname
		if isinstance(name, str):
			name = name.encode('utf-8')
		item = ResourceFileItem(name, content, compress, encrypt)
		self.files[name] = item

	def add_memory(self, name, content, compress=True, encrypt=True):
		if isinstance(name, str):
			name = name.encode('utf-8')
		if isinstance(content, str):
			content = content.encode()
		item = ResourceFileItem(name, content, compress, encrypt)
		self.files[name] = item

	def get(self, name):
		if isinstance(name, str):
			name = name.encode('utf-8')
		val = self.files[name]
		if isinstance(val, ResourceFileItem):
			return val.content
		return None

	def exist(self, name):
		if isinstance(name, str):
			name = name.encode('utf-8')
		return name in self.files.keys()

	def list(self):
		return self.files.keys()
