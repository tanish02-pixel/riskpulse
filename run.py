import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from riskpulse import config

if __name__ == "__main__":
    import uvicorn
    print("RiskPulse: http://" + config.HOST + ":" + str(config.PORT))
    print("API documentation: /docs. SQLite state: " + str(config.DB_PATH))
    uvicorn.run("riskpulse.app:app", host=config.HOST, port=config.PORT, workers=1)

