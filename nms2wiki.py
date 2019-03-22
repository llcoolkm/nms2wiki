#! /usr/bin/python3
#------------------------------------------------------------------------------
#
# WHO
#
#  km@grogg.org
#
# WHAT
#
#  Search dokuwiki for device documentation, retrieve selected values for the
#  device from LibreNMS and then update the device wiki page
#
#  Uses a YAML formatted config file nms2wiki.yml
#
# TODO
#
#  - Try make it more flexible and less dependent on a certain structure?
#  - Modularize LibreNMS API access?
#
#
#------------------------------------------------------------------------------
# Imports {{{
import argparse, json, ssl, fileinput, yaml, sys
from urllib.request import Request, urlopen
from os import listdir
from os.path import isfile, join
config = {}

# }}}
# def main(args) {{{
#------------------------------------------------------------------------------
def main(args):
	"""
	Load config, get list of devices and wiki file paths
	Get device data from LibreNMS and update the device wiki file
	"""

	global config
	hostname = args.host
	devicetype = args.type
	configfile = args.config
	quiet = args.quiet
	devices = {}

	# Load config
	with open(configfile, 'r') as stream:
		try:
			config = yaml.safe_load(stream)
		except yaml.YAMLError as e:
			print(e)

	# Create dictionary of devices with filename as value
	if devicetype:
		devices = get_wiki_devices(hostname, config['paths'][devicetype])
	else:
		for path in config['paths']:
			devices.update(get_wiki_devices(hostname, config['paths'][path]))

	# Get device data from LibreNMS
	for device in devices:
		nms_device = get_nms_device(device)[0]

		# Check that we can evaluate which os the device has
		if 'os' not in nms_device:
			if not quiet:
				print("WARNING: %s is missing from LibreNMS. Skipping." % device)

		else:
			update_wiki_file(device, devices[device], nms_device)

	return


# }}}
# update_wiki_file() {{{
#------------------------------------------------------------------------------
def update_wiki_file(device, wikifile, nms_device):
	"""
	Read wiki file, loop through it, change lines and write it back
	"""

	global config

	# Read wiki file to a list
	try:
		lines = [line.rstrip('\n') for line in open(wikifile, 'r')]
	except Exception as e:
		print(e)
		return

	# Loop the values that are configured for this OS
	try:
		for key in config['osvalues'][nms_device['os']]:

			charcount = len(config['headers'][key])
			varcount = config['templates'][key].count("%s")

			for i, line in enumerate(lines):

				# Check header and replace accordingly.
				if line[0:charcount] == config['headers'][key]:
					if varcount == 1:
						lines[i] = "%s|%s|" % (config['headers'][key],
							(config['templates'][key] % nms_device[key]))
					elif varcount == 2:
						lines[i] = "%s|%s|" % (config['headers'][key],
							(config['templates'][key] % (nms_device[key], device)))
					else:
						print("WARNING: Too many conversion literals in template. Skipping.")

	except KeyError:
		print("WARNING: %s doesnt have any osvalues defined in the configuration file. Dumping JSON data:" % device)
		print(json.dumps(nms_device, indent=4, sort_keys=True))
		return

	# Write back data to wiki file
	try:
		with open(wikifile, 'w') as f:
			f.write("\n".join(lines))
			f.close()
	except Exception as e:
		print(e)

	return


# }}}
# def get_wiki_devices(hostname, path) {{{
#------------------------------------------------------------------------------
def get_wiki_devices(hostname, path):
	"""
	"""

	global config
	devices = {}

	# Search folders in folders
	for dirname in listdir(path):
		dirname = join(path, dirname)
		if isfile(dirname):
			continue

		# Get device directories in dirname, these are our devices
		for devicename in listdir(dirname):
			fullpath = join(dirname, devicename)

			# Dont't process files or directory 'guides'
			if isfile(fullpath) or devicename == 'guides':
				continue

			# Should we get one named server or all servers we find?
			if hostname == None or hostname == devicename:
				devices[devicename] = fullpath + "/" + config['wikifile']

	return devices


# }}}
# def get_nms_device(hostname) {{{
#------------------------------------------------------------------------------
def get_nms_device(hostname):
	"""
	"""
	global config
	action = "devices/"

	# Get JSON object from IPAM
	ssl._create_default_https_context = ssl._create_unverified_context
	request = Request(config['url'] + action + hostname)
	request.add_header('X-Auth-Token', config['token'])
	data = urlopen(request).read().decode('utf-8')
	device = json.loads(data)

	return device['devices']


# }}}
# __main__ {{{
#------------------------------------------------------------------------------
if __name__ == '__main__':
	# Parse arguments
	parser = argparse.ArgumentParser(description='nms2wiki')
	parser.add_argument('--host', '-H', help='Host to retrieve info for')
	parser.add_argument('--type', '-t', help='Device types to retrieve info for, this is defined in the configureation file')
	parser.add_argument('--config', '-c', default='nms2wiki.yml', help='Configuration file. Default is "nms2wiki.yml"')
	parser.add_argument('--verbose', '-v', action='store_true', help='Verbose')
	parser.add_argument('--quiet', '-q', action='store_true', help='Quiet')
	args = parser.parse_args()
	main(args)


# }}}
