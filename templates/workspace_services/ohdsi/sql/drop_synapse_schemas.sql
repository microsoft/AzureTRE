/****** Copy Data ******/
CREATE TABLE #tbl
WITH
( DISTRIBUTION = ROUND_ROBIN
)
AS
SELECT  ROW_NUMBER() OVER(ORDER BY (SELECT NULL)) AS Sequence
,       [name]
,       'DROP TABLE ' + N'$(RESULTS_SCHEMA_NAME)' + '.' + name AS sql_code
FROM    sys.tables
WHERE schema_id = (select schema_id from sys.schemas where name = N'$(RESULTS_SCHEMA_NAME)')
;

DECLARE @nbr_statements INT = (SELECT COUNT(*) FROM #tbl)
,       @i INT = 1
;

WHILE   @i <= @nbr_statements
BEGIN
    DECLARE @sql_code NVARCHAR(4000) = (SELECT sql_code FROM #tbl WHERE Sequence = @i);
    EXEC    sp_executesql @sql_code;
    SET     @i +=1;
END

DROP TABLE #tbl;

/****** Drop Schemas ******/

DROP SCHEMA [$(RESULTS_SCHEMA_NAME)];
DROP SCHEMA [$(TEMP_SCHEMA_NAME)];
