from setuptools import setup, find_packages

with open("requirements.txt") as f:
    tmp = f.read().strip().split("\n")
    install_requires = [pos for pos in tmp if "://" not in pos]
    dependency_links = [pos for pos in tmp if "://" in pos]

setup(
    name="pytigon-lib",
    version="0.99",
    description="Pytigon library",
    author="Sławomir Chołaj",
    author_email="slawomir.cholaj@gmail.com",
    license="LGPLv3",
    packages=find_packages(),
    install_requires=install_requires,
    dependency_links=dependency_links,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3",
)
