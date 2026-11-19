IF COL_LENGTH(N'dbo.Reservations', N'cancel_reason') IS NULL
    ALTER TABLE dbo.Reservations ADD cancel_reason NVARCHAR(500) NULL;
GO
