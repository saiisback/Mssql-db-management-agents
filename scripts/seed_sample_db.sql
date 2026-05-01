-- ============================================================
-- Seed script: creates a realistic source DB to refresh from,
-- and an empty destination DB to refresh into.
--
-- Run this ONCE before your first refresh. Two ways to run it:
--   1. SSMS: open this file -> connect to your server -> Execute (F5)
--   2. sqlcmd: see seed.bat in the project root
-- ============================================================

USE master;
GO

-- ── Drop & recreate ProductionDB (the source) ─────────────
IF DB_ID('ProductionDB') IS NOT NULL
BEGIN
    ALTER DATABASE ProductionDB SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE ProductionDB;
END
GO
CREATE DATABASE ProductionDB;
GO

USE ProductionDB;
GO

CREATE TABLE dbo.Customers (
    CustomerId  INT IDENTITY(1,1) PRIMARY KEY,
    FirstName   NVARCHAR(100) NOT NULL,
    LastName    NVARCHAR(100) NOT NULL,
    Email       NVARCHAR(200) NOT NULL,
    PhoneNumber NVARCHAR(50)  NULL,
    Country     NVARCHAR(50)  NOT NULL,
    CreatedAt   DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

CREATE TABLE dbo.Orders (
    OrderId     INT IDENTITY(1,1) PRIMARY KEY,
    CustomerId  INT NOT NULL FOREIGN KEY REFERENCES dbo.Customers(CustomerId),
    Amount      DECIMAL(10,2) NOT NULL,
    Status      NVARCHAR(20)  NOT NULL,
    OrderedAt   DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

-- Generate 200 fake customers
;WITH N AS (
    SELECT TOP 200 ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS n
    FROM sys.all_objects a CROSS JOIN sys.all_objects b
)
INSERT INTO dbo.Customers (FirstName, LastName, Email, PhoneNumber, Country)
SELECT
    CHOOSE((n % 8) + 1, 'Alex','Sam','Jordan','Taylor','Riley','Morgan','Casey','Drew'),
    CHOOSE((n % 10) + 1, 'Patel','Kim','Garcia','Smith','Johnson','Lee','Brown','Davis','Wilson','Martinez'),
    CONCAT('user', n, '@example.com'),
    CONCAT('+1-555-0', RIGHT(CONCAT('000', n), 3)),
    CHOOSE((n % 5) + 1, 'USA','UK','India','Singapore','Germany')
FROM N;
GO

-- Generate ~600 fake orders
;WITH N AS (
    SELECT TOP 600 ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS n
    FROM sys.all_objects a CROSS JOIN sys.all_objects b
)
INSERT INTO dbo.Orders (CustomerId, Amount, Status)
SELECT
    ((n - 1) % 200) + 1,
    CAST((ABS(CHECKSUM(NEWID())) % 50000) / 100.0 AS DECIMAL(10,2)),
    CHOOSE((n % 4) + 1, 'pending','shipped','delivered','cancelled')
FROM N;
GO

CREATE INDEX IX_Orders_CustomerId ON dbo.Orders(CustomerId);
GO

PRINT 'ProductionDB seeded:';
SELECT 'Customers' AS tbl, COUNT(*) AS rows FROM dbo.Customers
UNION ALL
SELECT 'Orders', COUNT(*) FROM dbo.Orders;
GO

-- ── Drop & recreate StagingDB (the destination) ───────────
USE master;
GO
IF DB_ID('StagingDB') IS NOT NULL
BEGIN
    ALTER DATABASE StagingDB SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE StagingDB;
END
GO
CREATE DATABASE StagingDB;
GO

PRINT 'StagingDB created (empty — the refresh agent will overwrite this).';
GO

PRINT '';
PRINT '✅ Seed complete. You can now run:  run_refresh.bat';
GO
