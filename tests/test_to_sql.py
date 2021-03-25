import os
import pytest
import pandas as pd
import numpy as np

from nuvolos import get_connection, to_sql


@pytest.fixture
def df():
    return pd.DataFrame(
        {
            "col_string": list("abc"),
            "col_string_with_nan": ["a", np.nan, "c"],
            "col_string_with_none": ["a", None, "c"],
            # "col_bytes": [b"foo", b"bar", b"baz"], : Binary is not supported, as it's not a distinct Pandas type
            "col_unicode": ["foo", "bar", "baz"],
            "col_int": list(range(1, 4)),
            "col_uint": np.arange(3, 6).astype("u1"),
            "col_float": np.arange(4.0, 7.0, dtype="float64"),
            "col_float_with_nan": [2.0, np.nan, 3.0],
            "col_bool": [True, False, True],
            "col_datetime": pd.date_range("20130101", periods=3),
            "col_datetime_with_nat": [
                pd.Timestamp("20130101"),
                pd.NaT,
                pd.Timestamp("20130103"),
            ],
        }
    )


def test_df(df):
    print(df.info())
    print(df.head())


def test_no_quotes_no_index(df):
    conn = get_connection(
        username=os.getenv("TEST_USERNAME"),
        password=os.getenv("TEST_PASSWORD"),
        dbname=os.getenv("TEST_DBNAME"),
        schemaname=os.getenv("TEST_SCHEMANAME"),
    )
    to_sql(
        df=df,
        name="NO_QUOTES_NO_INDEX",
        con=conn,
        database=os.getenv("TEST_DBNAME"),
        schema=os.getenv("TEST_SCHEMANAME"),
        index=False,
        if_exists="replace"
    )
    conn.commit()
    df_r = pd.read_sql("SELECT * FROM NO_QUOTES_NO_INDEX;", con=conn)
    print(df.info())
    print(df.head())
    print(df_r.info())
    print(df_r.head())
    df_c = df.compare(df_r)
    assert len(df_c.index) == 0
