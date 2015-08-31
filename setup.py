from distutils.core import setup

setup(
    name='quarry',
    version='0.2.0',
    author='Barney Gale',
    author_email='barney@barneygale.co.uk',
    url='https://github.com/barneygale/quarry',
    license='MIT',
    description='Minecraft protocol library',
    long_description=open('README.rst').read(),
    install_requires=[
        'twisted >= 13.0.0',
        'cryptography >= 0.9',
    ],
    packages=[
        "quarry",
        "quarry.mojang",
        "quarry.net",
        "quarry.util"
    ],
    package_data={'quarry': ['data/*.csv']},
)
