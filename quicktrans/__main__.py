"""QuickTrans entry point — python3 -m quicktrans"""

import os

from quicktrans.config import CONFIG_FILE, load_config, first_run_wizard, is_config_complete
from quicktrans.log import setup_logging


def main():
    # Load or create config
    if not os.path.exists(CONFIG_FILE):
        config = first_run_wizard()
    else:
        config = load_config()

    if not is_config_complete(config):
        config = first_run_wizard()

    # Set up logging
    setup_logging(config)

    # Import daemon after config is ready (PyObjC needs careful init order)
    from quicktrans.daemon import main as daemon_main
    daemon_main(config)


if __name__ == "__main__":
    main()
