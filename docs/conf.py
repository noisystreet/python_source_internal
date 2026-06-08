# python-source-internal documentation build configuration file

import datetime

project = "python-source-internal"
author = "python-source-internal contributors"
copyright = f"{datetime.date.today().year}, {author}"

extensions = [
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx.ext.extlinks",
    "sphinxcontrib.mermaid",
]

templates_path = []
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

language = "zh_CN"

# -- Options for HTML output -------------------------------------------------
html_theme = "sphinx_rtd_theme"
html_static_path = []

# -- Intersphinx mapping -----------------------------------------------------
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

# -- External links -----------------------------------------------------------
extlinks = {
    "issue": ("https://github.com/python/cpython/issues/%s", "cpython#%s"),
    "gh": ("https://github.com/%s", "GitHub: %s"),
}
