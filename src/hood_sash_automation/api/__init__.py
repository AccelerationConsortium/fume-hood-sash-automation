"""Fume hood sash actuator REST API.

FastAPI service conforming to STATUS_SPEC v1.1
(``ac-organic-lab/docs/STATUS_SPEC.md``). Sub-modules:

* ``api_service`` - FastAPI app factory and ``main()`` entry point.
* ``models`` - vendored STATUS_SPEC Pydantic types.
* ``status_builder`` - state derivation + ``allowed_actions``.
* ``claims`` - in-process claim/heartbeat/release registry.
"""

__version__ = "1.1.0"
__author__ = "Fume Hood Automation Team"