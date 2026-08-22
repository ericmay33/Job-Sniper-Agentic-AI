-- 001_init: extensions only.
--
-- No tables yet. Tables arrive with the Pydantic contracts that need them, so
-- that the schema and the typed contract land in the same commit.
--
-- pgvector is enabled up front because it is the one extension that is not part
-- of a stock Postgres install: turning it on now proves the build succeeded,
-- rather than discovering a missing .dll at the moment embeddings are needed.

CREATE EXTENSION IF NOT EXISTS vector;
