import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="photoriver2",
    version="0.0.1",
    author="Aigars Mahinovs",
    author_email="aigarius@gmail.com",
    description="Photo collection sync service",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/aigarius/photoriver2",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)
