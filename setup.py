from setuptools import setup


setup(
    name='pyBOM',
    version=0.2,
    packages=['pyBOM'],
    install_requires=[
        'pandas',
        'anytree',
        'openpyxl'
    ]
)