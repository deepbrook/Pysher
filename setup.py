from pathlib import Path

from setuptools import setup


setup(
    name="Pysher",
    version="0.6.0b2",
    description="Pusher websocket client for python, based on Erik Kulyk's PythonPusherClient",
    long_description=Path(__file__).parent.joinpath('README.md').read_text(),
    long_description_content_type='text/markdown',
    keywords="pusher websocket client",
    author="Erik Kulyk",
    author_email="23okrs20+github@mykolab.com",
    license="MIT",
    url="https://github.com/nlsdfnbch/Pysher",
    install_requires=["websocket-client<=0.48"],
    python_requires='>= 3.5',
    packages=["pysher"],
    classifiers=[
        'Development Status :: 4 - Beta',
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
