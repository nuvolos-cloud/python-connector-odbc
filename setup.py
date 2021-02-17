from setuptools import setup


def readme():
    with open("README.md") as f:
        return f.read()


setup(
    name="nuvolos-odbc",
    version="0.4.0",
    description="The Nuvolos python library for database connectivity, internal PyODBC-based version",
    long_description=readme(),
    url="https://github.com/nuvolos-cloud/python-connector-odbc",
    author="Alphacruncher",
    author_email="support@nuvolos.cloud",
    license="MIT",
    packages=["nuvolos-odbc"],
    install_requires=["keyring", "pyodbc"],
    zip_safe=False,
)
