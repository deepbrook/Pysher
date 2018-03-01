from setuptools import setup

VERSION = "0.4.2"

requirements = ["websocket-client"]


def readme():
    with open('README.md') as f:
        return f.read()

setup(
    name="Pysher",
    version=VERSION,
    description="Pusher websocket client for python, based on Erik Kulyk's PythonPusherClient",
    long_description=readme(),
    keywords="pusher websocket client",
    author="Erik Kulyk",
    author_email="23okrs20+github@mykolab.com",
    license="MIT",
    url="https://github.com/nlsdfnbch/Pysher",
    install_requires=requirements,
    packages=["pysher"],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Internet',
        'Topic :: Software Development :: Libraries ',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)
