"""
Template file for the .gitignore file
"""

EXTENSION = ""
TEMPLATE = """
.*
!.gitignore
__pycache__

packages/
!packages/{author}/

keys.json
**/*private_key*
"""
DIR = "./"
