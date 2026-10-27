"""Permite correr las pruebas con o sin Streamlit instalado (usa un doble si falta)."""
import os
import sys
from unittest.mock import MagicMock

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

try:
    import streamlit  # noqa: F401
except ImportError:
    sys.modules["streamlit"] = MagicMock()
    for m in ["plotly", "plotly.express", "plotly.graph_objects", "plotly.subplots"]:
        sys.modules.setdefault(m, MagicMock())
