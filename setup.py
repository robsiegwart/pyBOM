from setuptools import setup


setup(
    name='pyBOM',
    version=0.1,
    packages=['pyBOM'],
    install_requires=[
        'pandas>=1.0.5',
        'anytree>=2.8.0'
    ],
    python_requires='>=3.5'
)