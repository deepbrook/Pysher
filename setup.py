from setuptools import setup, find_packages


setup(
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=["websocket-client!=0.49"],
)

