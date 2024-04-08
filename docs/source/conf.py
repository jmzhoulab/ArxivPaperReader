# Configuration file for the Sphinx documentation builder.

# -- Project information

project = 'ArxivDailyPaper'
copyright = '2024, JiamuZhou'
author = 'JiamuZhou'

release = ''
version = ''

# -- General configuration

extensions = [
    'sphinx.ext.duration',
    'sphinx.ext.doctest',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.intersphinx',
]

intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
}
intersphinx_disabled_domains = ['std']

templates_path = ['_templates']

source_suffix = ['.rst', '.md']

# -- Options for HTML output

html_theme = 'furo'   # 'sphinx_rtd_theme'
html_theme_options = {
    # "sidebar_hide_name": True,
    "light_css_variables": {
        "font-stack": "Helvetica, Arial, sans-serif, -apple-system",
        "font-stack--monospace": "Courier, monospace",
        "color-brand-primary": "#E5261F",
        "color-brand-content": "#E5261F",
        "admonition-font-size": "1rem",
        "admonition-title-font-size": "1rem",
        "font-size--small--2": "var(--font-size--small)",
    }
}


# -- Options for EPUB output
epub_show_urls = 'footnote'
