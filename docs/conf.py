# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
#import sys
#from pathlib import Path

#sys.path.append(str(Path('/sphinx/ext').resolve()))


project = 'Geo Pie'
copyright = '2024, gis56'
author = 'gis56'
release = '0.1'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = []

templates_path = ['_templates']
exclude_patterns = []

language = 'ru'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

#html_theme = 'classic'
html_theme = 'sphinx_rtd_theme'
html_theme_path = ["."]
#html_theme = 'furo'
#html_theme = 'alabaster'
html_static_path = ['_static']
