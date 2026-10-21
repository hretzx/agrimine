"""python -m api  [--port 8000] [--host 127.0.0.1]

On your own machine it listens on 127.0.0.1:8000. A host that hands out a port in the PORT variable (Render, Railway, Heroku ...)
needs the server to listen on 0.0.0.0 and on that port, so when PORT is set those become the defaults.
"""
import argparse
import os


def defaults(environ=os.environ) -> tuple[str, int]:
    port = environ.get("PORT")
    return ("0.0.0.0", int(port)) if port else ("127.0.0.1", 8000)


def main() -> None:
    import uvicorn

    host, port = defaults()
    parser = argparse.ArgumentParser(description="Run the AgriMine API (and the built web app when web/out exists).")
    parser.add_argument("--host", default=host)
    parser.add_argument("--port", type=int, default=port)
    args = parser.parse_args()
    uvicorn.run("api.main:app", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
