"""
	Functions that need to run prior to CI running unit tests
"""

import os
import shutil
from FloodMitigation import settings


def copy_local_settings():
	"""
		Takes the local_settings defaults file and creates the local_settings file with it so that the settings can be overridden on specific devices, but the CI will use the defaults
	:return:
	"""
	base_file = os.path.join(settings.BASE_DIR, "FloodMitigation", "_local_settings_defaults.py")
	output_file = os.path.join(settings.BASE_DIR, "FloodMitigation", "local_settings.py")
	shutil.copy(base_file, output_file)


if __name__ == "__main__":
	copy_local_settings()

