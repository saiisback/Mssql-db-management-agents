-- Placeholder environment patch script for non-prod refreshes.
-- Drop linked servers / disable production-only jobs / fix connection strings here.
-- Each batch separated by `GO` on its own line.

-- Example:
-- IF EXISTS (SELECT 1 FROM sys.servers WHERE name = 'PROD_LINKED_SERVER')
--   EXEC sp_dropserver 'PROD_LINKED_SERVER', 'droplogins';
-- GO

PRINT 'patch_environment.sql ran (no-op placeholder — populate with env-specific changes)';
GO
