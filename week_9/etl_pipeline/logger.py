import logging

log = logging.getLogger("etl")
log.setLevel(logging.INFO)

# Handler 1: console
console = logging.StreamHandler()
console.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

# Handler 2: file (mode="a" = append, không ghi đè)
file = logging.FileHandler("logs/etl.log", mode="a")
file.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

log.addHandler(console)
log.addHandler(file)