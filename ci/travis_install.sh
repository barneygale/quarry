#!/bin/bash

set -e

# Package dependencies
pip install twisted cryptography pyOpenSSL service_identity bitstring
# Test dependencies
pip install pytest

# Print versions
python --version
python -c "import twisted; print('twisted %s' % twisted.__version__)"
python -c "import cryptography; print('cryptography %s' % cryptography.__version__)"
python -c "import service_identity; print('service_identity %s' % service_identity.__version__)"

python setup.py build_ext --inplace
