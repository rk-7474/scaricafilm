import os
import uvicorn

def main():
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"Avvio ScaricaFilm WebUI su http://{host}:{port}")
    uvicorn.run("src.app:app", host=host, port=port, reload=False)

if __name__ == "__main__":
    main()