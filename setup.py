from setuptools import setup


setup(
    name='python-BOM',
    version=0.1,
    pymodules=['BOM.py'],
    install_requires=[
        'pandas>=1.0.5',
        'anytree>=2.8.0'
    ],
    python_requires='>=3.5'
)