from setuptools import setup, find_packages

setup(
    name='peaktech2510',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        # List your project's dependencies here.
        # They will be installed by pip when your project is installed.
        'matplotlib',
    ],
    description='Package to interface the PeakTech2510 Energy Meter'
)
