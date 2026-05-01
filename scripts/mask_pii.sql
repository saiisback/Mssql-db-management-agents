-- Placeholder PII masking script for non-prod refreshes.
-- Replace these statements with the actual columns / tables for your workload.
-- Each batch is separated by `GO` on its own line.

-- Example:
-- UPDATE dbo.Customers SET Email = CONCAT('user_', CAST(CustomerId AS VARCHAR(20)), '@example.invalid')
-- WHERE Email IS NOT NULL;
-- GO
-- UPDATE dbo.Customers SET PhoneNumber = '+1-555-0100' WHERE PhoneNumber IS NOT NULL;
-- GO

PRINT 'mask_pii.sql ran (no-op placeholder — populate with real masking statements)';
GO
