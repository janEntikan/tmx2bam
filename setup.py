import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="panda3d-tmx2bam",
    version="0.0.1",
    author="janEntikan",
    author_email="bandaibandai@rocketship.com",
    description="CLI tool for converting Tiled TMX files to Panda3D BAM files.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/janentikan/tmx2bam",
    packages=["tmx2bam"],
    install_requires=[
        "panda3d",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: CC0 1.0 Universal (CC0 1.0) Public Domain Dedication",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'console_scripts':[
            'tmx2bam=tmx2bam:main',
        ]
    }
)
