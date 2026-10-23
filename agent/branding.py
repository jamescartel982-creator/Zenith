"""Offline Zenith identity shared by the installer and interactive terminal."""
BANNER = """
#######  ######  ##   ##  ######  #######  ##   ##
    ##   ##      ###  ##    ##      ##    ##   ##
   ##    #####   ## # ##    ##      ##    #######
  ##     ##      ##  ###    ##      ##    ##   ##
#######  ######  ##   ##  ######    ##    ##   ##
""".strip('\n')


def show_banner():
    print('\n' + BANNER + '\n', flush=True)
