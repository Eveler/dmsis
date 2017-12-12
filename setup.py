# -*- encoding: utf-8 -*-
from setuptools import setup, find_packages, findall

__version__ = '1.0'

setup(
    name='dmsis',
    version=__version__,
    description='Directum SMEV integration system',
    license='GPL',
    scripts=['dmsis.py', 'db.py', 'declar.py', 'smev.py', 'six.py',
             'cached_property.py'],
    packages=find_packages(),
    # packages=findall(),
    package_data={
        'lxml': ['*.pyd', '*.h', '*.dll', '*.rng', '*.xsl', '*.txt', '*.pxd',
                 'includes/*.pxd']
    },
    include_package_data=True,
    entry_points={'console_scripts': ['dmsis = dmsis:main']},
    install_requires=['setuptools', 'win32core', 'win32compat', 'win32ext']
)
