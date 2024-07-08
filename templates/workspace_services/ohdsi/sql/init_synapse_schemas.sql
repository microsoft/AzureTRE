/****** Results and temp Schema creation ******/

CREATE SCHEMA [$(RESULTS_SCHEMA_NAME)]
GO

CREATE SCHEMA [$(TEMP_SCHEMA_NAME)]
GO

/****** Copy Data ******/
CREATE TABLE #tbl
WITH
( DISTRIBUTION = ROUND_ROBIN
)
AS
SELECT ROW_NUMBER() OVER(ORDER BY (SELECT NULL)) AS Sequence
,      [name]
,      'CREATE TABLE ' + N'$(RESULTS_SCHEMA_NAME)' + '.' + t.name + ' WITH (DISTRIBUTION = ' + d.distribution_policy_desc + ', CLUSTERED COLUMNSTORE INDEX) AS SELECT * FROM ' +  N'$(ORIGIN_RESULTS_SCHEMA_NAME)' + '.' + t.name AS sql_code
FROM sys.tables AS t left join  sys.pdw_table_distribution_properties AS d ON (t.object_id = d.object_id)
WHERE t.schema_id = (select schema_id from sys.schemas where name =  N'$(ORIGIN_RESULTS_SCHEMA_NAME)')
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
