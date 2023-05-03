import subprocess

import requests


def github(repo):
	headers = {'Accept': 'application/json'}
	r = requests.get(f"https://api.github.com/repos/{repo}/releases/latest", headers=headers)
	return r.json()["tag_name"]


def git(url):
	print("Getting latest version of " + url)

	subproc = subprocess.run(['git', '-c', 'versionsort.suffix=-', 'ls-remote', '--tags', '--sort=v:refname', url], text=True, stdout=subprocess.PIPE)

	return subproc.stdout.splitlines()[-1].split()[1][10:]

def llvm():
	return github("llvm/llvm-project")[8:]
