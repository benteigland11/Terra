"""Setuptools release-build safeguards for Terra.

Setuptools normally reuses ``build/lib``. That can put Python modules deleted
from the source tree into a later wheel, so every wheel build starts from an
empty build library.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py


class BuildPy(_build_py):
    """Prevent stale ignored build output from leaking into release wheels."""

    _CARTOGRAPH_IMPORT_ALIASES = {
        "cg/cg_infra_agent_cli_python": "cg/infra_agent_cli_python",
        "cg/cg_universal_agent_response_python": "cg/universal_agent_response_python",
    }

    def run(self) -> None:
        build_lib = Path(self.build_lib)
        if build_lib.exists():
            shutil.rmtree(build_lib)
        super().run()
        for source, target in self._CARTOGRAPH_IMPORT_ALIASES.items():
            shutil.copytree(
                Path(source) / "src",
                build_lib / target / "src",
                ignore=shutil.ignore_patterns("__pycache__", "*.py[co]"),
            )


setup(cmdclass={"build_py": BuildPy})
