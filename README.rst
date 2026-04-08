cliptrans
=========

.. image:: https://img.shields.io/github/actions/workflow/status/gaato/cliptrans/ci.yml?branch=main&label=CI
   :target: https://github.com/gaato/cliptrans/actions/workflows/ci.yml
   :alt: CI

.. image:: https://img.shields.io/badge/python-3.14%2B-blue
   :target: https://www.python.org/
   :alt: Python 3.14+

.. image:: https://img.shields.io/badge/license-AGPL--3.0--or--later-green
   :target: https://github.com/gaato/cliptrans/blob/main/LICENSE
   :alt: License

.. image:: https://img.shields.io/badge/docs-DeepWiki-4c8bf5
   :target: https://deepwiki.com/gaato/cliptrans
   :alt: DeepWiki

cliptrans is a tool for producing translated clips from streams and video sources.
It provides a CLI for subtitle generation and translation export, and a Web UI for browsing
streams and reviewing clip candidates.


Features
--------

* Run jobs from a video URL or a local file
* Transcribe audio with faster-whisper and regroup segments into utterances
* Translate utterances with an LLM and export SRT / VTT / ASS outputs
* Browse streams and review clip candidates in the Web UI
* Persist job state and clip data in SQLite so jobs can be resumed


Requirements
------------

* Python 3.14 or newer
* ``uv``
* ``ffmpeg`` and ``ffprobe``
* An LLM API key for translation or clip candidate extraction
* A Holodex API key for stream browsing in the Web UI

CPU execution is possible, but GPU is recommended for ASR workloads.


Setup
-----

For CLI usage only:

.. code-block:: bash

   uv sync

For CLI and Web UI:

.. code-block:: bash

   uv sync --extra web

Configure the application with ``cliptrans.toml``, ``glossary.toml``, or ``.env`` as needed.
At minimum, translation requires an API key.

.. code-block:: bash

   export CLIPTRANS_OPENAI_API_KEY=...
   export CLIPTRANS_HOLODEX_API_KEY=...


CLI
---

Run from a video URL:

.. code-block:: bash

   uv run cliptrans run "https://youtu.be/XXXX" --start 3600 --end 3900

Run from a local file:

.. code-block:: bash

   uv run cliptrans run --local-file ./video.mp4 --source-lang ja --target-lang en

Generate subtitles without translation:

.. code-block:: bash

   uv run cliptrans run --local-file ./video.mp4 --no-translate

List jobs and inspect a job:

.. code-block:: bash

   uv run cliptrans jobs
   uv run cliptrans show <job-id>

Outputs are typically written to ``data/jobs/<job-id>/output``.


Web UI
------

.. code-block:: bash

   uv run cliptrans-web

Open ``http://127.0.0.1:8000/`` in a browser after startup.

The Web UI supports:

* Browsing streams
* Viewing stream details
* Extracting clip candidates from subtitles
* Saving, approving, and rejecting candidates

Stream browsing features require a Holodex API key.


Configuration Files
-------------------

``cliptrans.toml``
   Main runtime configuration, including data paths, ASR settings, translation model,
   and Web UI host and port.

``glossary.toml``
   Proper noun corrections for ASR and glossary entries for translation.

Configuration precedence is approximately:

.. code-block:: text

   arguments > environment variables > .env > cliptrans.toml / glossary.toml


Architecture
------------

More detailed architecture and configuration notes are available in the DeepWiki reference above.

.. code-block:: text

   CLI / FastAPI
        |
        v
   application services
   (pipeline, clip finder, stream browser)
        |
        v
   adapters
   (yt-dlp, ffmpeg, faster-whisper, PydanticAI, Holodex, SQLAlchemy)
        |
        v
   external tools / services / storage
   (YouTube, LLM API, Holodex, SQLite, local files)

The codebase is organized as follows:

* ``src/cliptrans/entrypoints``: CLI and FastAPI entrypoints
* ``src/cliptrans/application``: use cases and services
* ``src/cliptrans/adapters``: external tools, external APIs, and persistence
* ``src/cliptrans/domain``: models and enums


Directory Layout
----------------

.. code-block:: text

   src/cliptrans/
     adapters/
     application/
     domain/
     entrypoints/
   tests/
   cliptrans.toml
   glossary.toml


License
-------

Licensed under ``AGPL-3.0-or-later``. See ``LICENSE`` for details.
