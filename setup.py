from distutils.core import setup

setup(
    name='quarry',
    version='1.2',
    author='Barney Gale',
    author_email='barney@barneygale.co.uk',
    url='https://github.com/barneygale/quarry',
    license='MIT',
    description='Minecraft protocol library',
    long_description=open('README.rst').read(),
    install_requires=[
        'cached_property >= 1.2.0',
        'twisted >= 13.0.0',
        'cryptography >= 0.9',
        'pyOpenSSL >= 0.15.1',
        'service_identity >= 14.0.0',
    ],
    test_requires=[
        'pytest'
    ],
    packages=[
        "quarry",
        "quarry.data",
        "quarry.net",
        "quarry.types",
        "quarry.types.buffer",
    ],
    package_data={'quarry': ['data/packets/*.csv']},
)
