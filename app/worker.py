from app.core.logging import configure_logging


def main() -> None:
    configure_logging()
    print("Drafft worker placeholder running. Replace with Celery/Temporal worker.")


if __name__ == "__main__":
    main()
