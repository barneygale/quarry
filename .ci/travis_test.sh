#!/bin/bash

set -e

# Print versions
python --version
python -c "import twisted; print('twisted %s' % twisted.__version__)"
python -c "import cryptography; print('cryptography %s' % cryptography.__version__)"
python -c "import pyOpenSSL; print('pyOpenSSL %s' % pyOpenSSL.__version__)"
python -c "import service_identity; print('service_identity %s' % service_identity.__version__)"

pytest
