#!/usr/bin/env python3
import sys
from cli.client import C2Client
from cli.app import C2App


def main():
    server = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:4444'
    client = C2Client(server)
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
