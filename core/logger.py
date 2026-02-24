import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    force=True,  # Ensures this config applies even if other libs init logging first
)

logger = logging.getLogger("sylemax")
