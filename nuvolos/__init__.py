import os
import logging
import pyodbc as pyodbc
import re
from urllib.parse import quote
import keyring
import getpass
from .sql_utils import to_sql, _quote_name
from .version import __version__

logger = logging.getLogger(__name__)


def load_env_var(env_var_name, description, print_value=False):
    var = os.getenv(env_var_name)
    if var is None:
        logger.debug(f"Could not find {description} in env var {env_var_name}")
    else:
        if print_value:
            logger.debug(f"Found {description} {var} in env var {env_var_name}")
        else:
            logger.debug(f"Found {description} in env var {env_var_name}")
    return var


def credd_from_env_vars():
    username = load_env_var("NUVOLOS_USERNAME", "username", print_value=True)
    password = load_env_var("NUVOLOS_SF_TOKEN", "Snowflake token", print_value=False)
    if username is None or password is None:
        return None
    else:
        return {"username": username, "snowflake_access_token": password}


def credd_from_secrets():
    username_filename = os.getenv("NUVOLOS_USERNAME_FILENAME", "/secrets/username")
    snowflake_access_token_filename = os.getenv(
        "NUVOLOS_SNOWFLAKE_ACCESSS_TOKEN_FILENAME",
        "/secrets/snowflake_access_token",
    )
    if not os.path.exists(username_filename):
        logger.debug(f"Could not find secret file {username_filename}")
        return None
    if not os.path.exists(snowflake_access_token_filename):
        logger.debug(f"Could not find secret file {snowflake_access_token_filename}")
        return None
    with open(username_filename) as username, open(
        snowflake_access_token_filename
    ) as access_token:
        username = username.readline()
        password = access_token.readline()
        logger.debug("Found username and Snowflake access token in /secrets files")
        return {"username": username, "snowflake_access_token": password}


def username_from_secrets():
    username_filename = os.getenv("NUVOLOS_USERNAME_FILENAME", "/secrets/username")
    if not os.path.exists(username_filename):
        logger.warning(f"Could not find secret file {username_filename}")
        return None
    with open(username_filename) as username:
        username = username.readline()
        logger.debug("Found username in /secrets file")
        return username


def input_nuvolos_credential():
    # store username & password
    username = getpass.getpass("Please input your Nuvolos username:")
    keyring.set_password("nuvolos", "username", username)

    password = getpass.getpass("Please input your Nuvolos password:")
    keyring.set_password("nuvolos", username, password)


def credd_from_local():
    # retrieve username & password
    username = keyring.get_password("nuvolos", "username")
    password = keyring.get_password("nuvolos", username)
    return {"username": username, "snowflake_access_token": password}


def dbpath_from_file(path_filename):
    if not os.path.exists(path_filename):
        logger.debug(f"Could not find dbpath file {path_filename}")
        return None
    with open(path_filename, "r") as path_file:
        lines = path_file.readlines()
        if len(lines) == 0:
            logger.debug(f"Could not parse dbpath file: {path_filename} is empty.")
            return None
        first_line = lines[0].rstrip()
        if "Tables are not enabled" in first_line:
            raise Exception(
                "Tables are not enabled for this space, please enable them first in the space settings."
            )
        # Split at "." character
        # This should have resulted in two substrings
        split_arr = re.split('"."', first_line)
        if len(split_arr) != 2:
            logger.debug(
                f'Could not parse dbpath file: pattern "." not found in {path_filename}. '
                f"Are the names escaped with double quotes?"
            )
            return None
        # Remove the remaining double quotes, as we'll escape those
        db_name = split_arr[0].replace('"', "")
        schema_name = split_arr[1].replace('"', "")
        logger.debug(
            f"Found database = {db_name}, schema = {schema_name} in dbpath file {path_filename}."
        )
        return {"db_name": db_name, "schema_name": schema_name}


def dbpath_from_env_vars():
    db_name = load_env_var("NUVOLOS_DB", "Snowflake database", print_value=True)
    schema_name = load_env_var("NUVOLOS_SCHEMA", "Snowflake schema", print_value=True)
    if db_name is None or schema_name is None:
        return None
    return {"db_name": db_name, "schema_name": schema_name}


def get_connection_string(username=None, password=None, dbname=None, schemaname=None):
    if username is None and password is None:
        if os.getenv("SNOWFLAKE_RSA_KEY"):
            username = os.getenv("") or username_from_secrets()
        else:
            credd = credd_from_env_vars() or credd_from_secrets() or credd_from_local()
            if credd is None:
                input_nuvolos_credential()
                credd = credd_from_local()

            username = credd["username"]
            password = credd["snowflake_access_token"]
    elif (
        username is not None and password is None and not os.getenv("SNOWFLAKE_RSA_KEY")
    ):
        raise ValueError(
            "You have provided a username but not a password. "
            "Please either provide both arguments or leave both arguments empty."
        )
    elif username is None and password is not None:
        raise ValueError(
            "You have provided a password but not a username. "
            "Please either provide both arguments or leave both arguments empty."
        )
    else:
        logger.debug("Found username and Snowflake access token as input arguments")

    if dbname is None and schemaname is None:
        path_filename = os.getenv("NUVOLOS_DBPATH_FILE", "/lifecycle/.dbpath")
        dbd = (
            dbpath_from_file(path_filename)
            or dbpath_from_file(".dbpath")
            or dbpath_from_env_vars()
        )
        if dbd is None:
            raise ValueError(
                "Could not find Snowflake database and schema in .dbpath files or env vars. "
                "If you're not using this function from Nuvolos, "
                "please specify the Snowflake database and schema names as input arguments"
            )
        else:
            db_name = dbd["db_name"]
            schema_name = dbd["schema_name"]
    elif dbname is not None and schemaname is None:
        raise ValueError(
            "You have provided a dbname argument but not a schemaname argument. "
            "Please either provide both or provide none of them."
        )
    elif dbname is None and schemaname is not None:
        raise ValueError(
            "You have provided a schemaname argument but not a dbname argument. "
            "Please either provide both or provide none of them."
        )
    else:
        db_name = dbname
        schema_name = schemaname
        logger.debug("Found database and schema as input arguments")

    default_snowflake_host = (
        "acstg.eu-central-1" if "STAGING/" in db_name else "alphacruncher.eu-central-1"
    )
    snowflake_host = os.getenv("NUVOLOS_SNOWFLAKE_HOST", default_snowflake_host)
    connection_string = f"DRIVER=SnowflakeDSIIDriver;SERVER={snowflake_host}.snowflakecomputing.com;DATABASE=%22{quote(db_name)}%22;SCHEMA=%22{quote(schema_name)}%22;UID={username}"
    masked_connection_string = f"DRIVER=SnowflakeDSIIDriver;SERVER={snowflake_host}.snowflakecomputing.com;DATABASE=%22{quote(db_name)}%22;SCHEMA=%22{quote(schema_name)}%22;UID={username}"

    if os.getenv("SNOWFLAKE_RSA_KEY"):
        connection_string += f";AUTHENTICATOR=SNOWFLAKE_JWT;PRIV_KEY_FILE={os.getenv('SNOWFLAKE_RSA_KEY')}"
        masked_connection_string += f";AUTHENTICATOR=SNOWFLAKE_JWT;PRIV_KEY_FILE={os.getenv('SNOWFLAKE_RSA_KEY')}"
        if os.getenv("SNOWFLAKE_RSA_KEY_PASSPHRASE"):
            connection_string += (
                f";PRIV_KEY_FILE_PWD={os.getenv('SNOWFLAKE_RSA_KEY_PASSPHRASE')}"
            )
            masked_connection_string += ";PRIV_KEY_FILE_PWD=************"
    else:
        connection_string += f";PWD={password}"
        masked_connection_string += ";PWD=************"

    params = (
        ";CLIENT_METADATA_REQUEST_USE_CONNECTION_CTX=TRUE"
        + ";VALIDATEDEFAULTPARAMETERS=TRUE"
    )
    connection_string = connection_string + params
    masked_connection_string = masked_connection_string + params
    logger.debug("Built ODBC connection string: " + masked_connection_string)
    return connection_string, db_name, schema_name


def get_connection(*args, **kwargs):
    if len(args) == 2:
        username = None
        password = None
        dbname = args[0]
        schemaname = args[1]
    elif len(args) == 3:
        username = args[0]
        dbname = args[1]
        schemaname = args[2]
    elif len(args) == 4:
        username = args[0]
        password = args[1]
        dbname = args[2]
        schemaname = args[3]
    else:
        username = kwargs.get("username")
        password = kwargs.get("password")
        dbname = kwargs.get("dbname")
        schemaname = kwargs.get("schemaname")

    connection_string, db_name, schema_name = get_connection_string(
        username, password, dbname, schemaname
    )
    pyodbc.lowercase = True
    conn = pyodbc.connect(connection_string)
    conn.setencoding("utf-8")
    conn.setdecoding(pyodbc.SQL_CHAR, encoding="utf-8")
    conn.execute(f"USE SCHEMA {_quote_name(db_name)}.{_quote_name(schema_name)};")
    return conn
