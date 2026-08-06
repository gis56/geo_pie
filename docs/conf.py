# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import sys
import os

#from pathlib import Path
#sys.path.append(str(Path('/usr/lib').resolve()))
#sys.path.append(str(Path('/sphinx/ext').resolve()))

sys.path.insert(0,  os.path.abspath('../'))

project = 'Geo Pie'
copyright = '2024, gis56'
author = 'gis56'
release = '0.1'

master_doc = 'index'
pygments_style = 'sphinx'
source_suffix = '.rst'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode'
]

templates_path = ['_templates']
exclude_patterns = [
    '_build',
    'Thumbs.db',
    '.DS_Store',
]

language = 'ru'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_show_sourcelink = True
#html_theme = 'sphinx_book_theme'
html_theme = 'sphinx_rtd_theme'
#html_theme = 'furo'
#html_theme = 'alabaster'
html_static_path = ['_static']
html_logo = 'image/geopie.png'
#html_theme_options = {
#    'logo_only': True,
#    'display_version': False,
#}
