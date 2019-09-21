from setuptools import setup, find_packages

setup(
    name="pytigon-lib",
    version="0.9",
    description="Pytigon library",
    author="Sławomir Chołaj",
    author_email="slawomir.cholaj@gmail.com",
    packages=find_packages(),
    install_requires=[
        "fpdf",
        "requests",
        "openpyxl",
        "httpie",
        "fs",
        "pyexcel_odsr",
        "pendulum",
        "Django<2.2.5",
        "cffi",
        "Pillow",
        "lxml",
    ],
)
