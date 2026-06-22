import argparse
import sys

from cli.client import C2Client
from cli.app import C2App


def main():
    parser = argparse.ArgumentParser(description='RogueByte C2 CLI')
    parser.add_argument('--server', '-s', default='http://localhost:4444',
                        help='C2 server URL (default: http://localhost:4444)')
    args = parser.parse_args()

    client = C2Client(args.server)
    app = C2App(client)
    try:
        app.run()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            client.disconnect()
        except Exception:
            pass


if __name__ == '__main__':
    main()
