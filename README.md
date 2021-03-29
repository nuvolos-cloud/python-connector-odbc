# Nuvolos connector for Python (PyODBC version, for internal use)

This package allows you to read table data from Nuvolos and upload Pandas dataframes as tables.

## Loading data to Nuvolos

This package provides a `to_sql` function, which bulk loads a Pandas DataFrame to Nuvolos.
This function is able to load large DataFrames quickly and efficiently, using the database engine's bulk data ingestion process.
It is based on the `write_pandas` function of the `snowflake-connector-python` package.

### Note:
It is recommended to use lowercase DataFrame column and index names.
Uppercase or mixed-case DataFrame column/index names will result in case-sensitive table name and column names, which can be queried with quoted identifiers.


### Syntax:
```python
def to_sql(
    df,
    name,
    con,
    database=None,
    schema=None,
    if_exists="fail",
    index=True,
    index_label=None,
    nanoseconds=False,
):
    """
    Load a DataFrame to the specified table in the database.
    Creates the table if it doesn't yet exist, with TEXT/FLOAT/DATE/TIMESTAMP columns as required.
    The name will be case sensitive (quoted) if it contains lowercase or special characters or is a reserved keyword.
    Based on the write_pandas function of snowflake-connector-python:
    https://docs.snowflake.com/en/user-guide/python-connector-api.html#write_pandas
    :param df: The Pandas DataFrame to insert/stage as a table.
    :param name: The name of the database table. It will only be quoted and case sensitive if it contains keywords or special chars.
    :param con: The pre-opened database Connection to use.
    :param database: The name of the database to which data will be inserted.
    :param schema: The name of the schema to which data will be inserted.
    :param if_exists: How to behave if the table already exists. {‘fail’, ‘replace’, ‘append’}, default ‘fail’
             * fail: Raise a ValueError.
             * replace: Drop the table before inserting new values.
             * append: Insert new values to the existing table.
    :param index: bool, default True: Write DataFrame index as a column. Uses index_label as the column name in the table.
    :param index_label: Column label for index column(s). If None is given (default) and index is True, then the index names are used. A sequence should be given if the DataFrame uses MultiIndex.
    :param nanoseconds: If True, nanosecond timestamps will be used to upload the data. Limits timestamp range from 1677-09-21 00:12:43.145224192 to 2262-04-11 23:47:16.854775807.
    :return: Returns the COPY INTO command's results to verify ingestion in the form of a tuple of whether all chunks were
        ingested correctly, # of chunks, # of ingested rows, and ingest's output.
    """
```

### Usage example:
In this example, the DataFrame will be loaded to a table named "quotes_AND_index", which is a case-sensitive name.
```python
from nuvolos import get_connection, to_sql
import pandas as pd

conn = get_connection()
to_sql(
    df=df,
    name="lowercase_is_best",
    con=conn,
    index=True,
    index_label="seq_num",
    if_exists="replace"
)
df_r = pd.read_sql('SELECT * FROM lowercase_is_best;', con=conn, index_col="seq_num")
df_c = df.compare(df_r) # Will be an empty DataFrame, as there are no differences.
```
