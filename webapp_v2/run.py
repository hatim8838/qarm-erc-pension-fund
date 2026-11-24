"""Convenience launcher: ``python run.py`` starts the app on ``config.PORT``."""

import sys

from streamlit.web import cli

import config as cfg

if __name__ == "__main__":
    sys.argv = ["streamlit", "run", str(cfg.APP_DIR / "app.py"), "--server.port", str(cfg.PORT)]
    sys.exit(cli.main())
