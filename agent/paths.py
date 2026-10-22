"""Stable user paths for source checkouts and installed command-line use."""
import os
from pathlib import Path


def zenith_home():
    override = os.getenv('ZENITH_HOME')
    if override:
        return Path(override).expanduser().resolve()
    if os.name == 'nt':
        return Path(os.getenv('LOCALAPPDATA', str(Path.home() / 'AppData' / 'Local'))) / 'Zenith'
    return Path(os.getenv('XDG_DATA_HOME', str(Path.home() / '.local' / 'share'))) / 'zenith'


def config_file():
    return Path(os.getenv('ZENITH_CONFIG_FILE', str(zenith_home() / 'config.env'))).expanduser().resolve()


def default_data_dir():
    # Preserve existing source-checkout conversations during upgrades.
    legacy = Path.cwd() / 'data'
    if (legacy / 'zenith.sqlite3').is_file():
        return str(legacy.resolve())
    return str(zenith_home() / 'data')
