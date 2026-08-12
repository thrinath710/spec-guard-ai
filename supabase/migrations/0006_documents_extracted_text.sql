-- Store the extracted text alongside the document.
--
-- Uploaded files live on the host's local disk, which is ephemeral on most platform-as-a-service
-- hosts: the container is replaced on every deploy and free instances are recycled when idle.
-- Without the text persisted, re-running an earlier analysis fails because the source file is
-- gone. Keeping the text means a re-run never depends on the original upload surviving.
alter table documents
  add column if not exists extracted_text text;
