import os
import sys

project = 'RoCEv2 Integration in Rogue'
copyright = '2025, SLAC National Accelerator Laboratory'
author = 'SLAC National Accelerator Laboratory'
release = '1.0'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
    'sphinx_copybutton',
    'myst_parser',
]

templates_path = ['_templates']
exclude_patterns = []

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_theme_options = {
    'navigation_depth': 4,
    'collapse_navigation': False,
    'sticky_navigation': True,
    'includehidden': True,
    'titles_only': False,
}

myst_enable_extensions = [
    'colon_fence',
    'deflist',
    'tasklist',
]

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
}

source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}
