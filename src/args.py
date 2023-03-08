import argparse


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Process some integers.")
    parser.add_argument("--jobs", action="store_true", help="listen on job events")
    parser.add_argument(
        "--locusts", action="store_true", help="listen on locust and events"
    )
    return parser.parse_args()
