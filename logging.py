enable_logging = True

def log(message: str) -> None:
    if enable_logging:
        print(f"[LOG]: {message}")
