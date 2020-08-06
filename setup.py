from setuptools import setup


setup(
    name='pybom',
    version=0.1,
    pymodules=['BOM.py'],
    entry_points={
        'console_scripts': [
            'pybom = BOM:build'
        ]
    },
    install_requires=[
        'click>=7.1.1',
        'pyyaml>=5.3.1',
        'pdfkit>=0.6.1',
        'jinja2>=2.11.1'
    ],
    python_requires='>=3.5'
)